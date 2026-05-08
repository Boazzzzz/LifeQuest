from datetime import datetime, timezone

from app.models.japanese import JapaneseVerbForm, JapaneseVerbFormCreate, JapaneseVerbGroup
from app.repositories.japanese import JapaneseRepository


class JapaneseVerbFormNotFoundError(ValueError):
    pass


class JapaneseVerbConjugationError(ValueError):
    pass


class JapaneseService:
    def __init__(self, repository: JapaneseRepository | None = None) -> None:
        self.repository = repository or JapaneseRepository()

    def create_verb_form(self, payload: JapaneseVerbFormCreate) -> JapaneseVerbForm:
        generated = self._generate_core_forms(payload.dictionary_form, payload.verb_group)
        forms = {
            "plain_nonpast": payload.plain_nonpast or generated.get("plain_nonpast"),
            "polite_nonpast": payload.polite_nonpast or generated.get("polite_nonpast"),
            "plain_past": payload.plain_past or generated.get("plain_past"),
            "polite_past": payload.polite_past or generated.get("polite_past"),
            "plain_negative": payload.plain_negative or generated.get("plain_negative"),
            "polite_negative": payload.polite_negative or generated.get("polite_negative"),
            "plain_negative_past": payload.plain_negative_past or generated.get("plain_negative_past"),
            "polite_negative_past": payload.polite_negative_past or generated.get("polite_negative_past"),
        }
        missing = [name for name, value in forms.items() if not value]
        if missing:
            raise JapaneseVerbConjugationError(
                f"Cannot infer {', '.join(missing)} for {payload.dictionary_form}; provide forms manually."
            )

        now = datetime.now(timezone.utc)
        verb_form = JapaneseVerbForm(
            dictionary_form=payload.dictionary_form,
            reading=payload.reading,
            meaning=payload.meaning,
            verb_group=payload.verb_group,
            jlpt_level=payload.jlpt_level,
            confidence=payload.confidence,
            plain_nonpast=forms["plain_nonpast"],
            polite_nonpast=forms["polite_nonpast"],
            plain_past=forms["plain_past"],
            polite_past=forms["polite_past"],
            plain_negative=forms["plain_negative"],
            polite_negative=forms["polite_negative"],
            plain_negative_past=forms["plain_negative_past"],
            polite_negative_past=forms["polite_negative_past"],
            notes=payload.notes,
            tags=payload.tags,
            created_at=now,
            updated_at=now,
        )
        return self.repository.create_verb_form(verb_form)

    def list_verb_forms(self, limit: int = 100) -> list[JapaneseVerbForm]:
        return self.repository.list_verb_forms(limit=limit)

    def get_verb_form(self, verb_form_id: str) -> JapaneseVerbForm:
        verb_form = self.repository.get_verb_form(verb_form_id)
        if verb_form is None:
            raise JapaneseVerbFormNotFoundError(f"Japanese verb form not found: {verb_form_id}")
        return verb_form

    def seed_basic_verb_forms(self) -> list[JapaneseVerbForm]:
        seeds = [
            JapaneseVerbFormCreate(
                dictionary_form="食べる",
                reading="たべる",
                meaning="eat",
                verb_group=JapaneseVerbGroup.ichidan,
                tags=["sample", "ichidan"],
            ),
            JapaneseVerbFormCreate(
                dictionary_form="書く",
                reading="かく",
                meaning="write",
                verb_group=JapaneseVerbGroup.godan,
                tags=["sample", "godan"],
            ),
            JapaneseVerbFormCreate(
                dictionary_form="する",
                reading="する",
                meaning="do",
                verb_group=JapaneseVerbGroup.suru,
                tags=["sample", "irregular"],
            ),
            JapaneseVerbFormCreate(
                dictionary_form="来る",
                reading="くる",
                meaning="come",
                verb_group=JapaneseVerbGroup.kuru,
                tags=["sample", "irregular"],
            ),
        ]
        return [self.create_verb_form(seed) for seed in seeds]

    def _generate_core_forms(self, dictionary_form: str, verb_group: JapaneseVerbGroup) -> dict[str, str]:
        if verb_group == JapaneseVerbGroup.ichidan:
            return self._generate_ichidan(dictionary_form)
        if verb_group == JapaneseVerbGroup.godan:
            return self._generate_godan(dictionary_form)
        if verb_group == JapaneseVerbGroup.suru:
            return self._generate_suru(dictionary_form)
        if verb_group == JapaneseVerbGroup.kuru:
            return self._generate_kuru(dictionary_form)
        return {}

    def _generate_ichidan(self, dictionary_form: str) -> dict[str, str]:
        if not dictionary_form.endswith("る"):
            raise JapaneseVerbConjugationError("Ichidan verbs should end with る.")
        stem = dictionary_form[:-1]
        return {
            "plain_nonpast": dictionary_form,
            "polite_nonpast": f"{stem}ます",
            "plain_past": f"{stem}た",
            "polite_past": f"{stem}ました",
            "plain_negative": f"{stem}ない",
            "polite_negative": f"{stem}ません",
            "plain_negative_past": f"{stem}なかった",
            "polite_negative_past": f"{stem}ませんでした",
        }

    def _generate_godan(self, dictionary_form: str) -> dict[str, str]:
        i_row = {
            "う": "い",
            "く": "き",
            "ぐ": "ぎ",
            "す": "し",
            "つ": "ち",
            "ぬ": "に",
            "ぶ": "び",
            "む": "み",
            "る": "り",
        }
        a_row = {
            "う": "わ",
            "く": "か",
            "ぐ": "が",
            "す": "さ",
            "つ": "た",
            "ぬ": "な",
            "ぶ": "ば",
            "む": "ま",
            "る": "ら",
        }
        past_suffix = {
            "う": "った",
            "つ": "った",
            "る": "った",
            "む": "んだ",
            "ぶ": "んだ",
            "ぬ": "んだ",
            "く": "いた",
            "ぐ": "いだ",
            "す": "した",
        }
        ending = dictionary_form[-1]
        if ending not in i_row:
            raise JapaneseVerbConjugationError(f"Unsupported godan ending: {ending}")

        base = dictionary_form[:-1]
        polite_stem = f"{base}{i_row[ending]}"
        negative_stem = f"{base}{a_row[ending]}"
        if dictionary_form in {"行く", "いく"}:
            plain_past = f"{base}った"
        else:
            plain_past = f"{base}{past_suffix[ending]}"

        return {
            "plain_nonpast": dictionary_form,
            "polite_nonpast": f"{polite_stem}ます",
            "plain_past": plain_past,
            "polite_past": f"{polite_stem}ました",
            "plain_negative": f"{negative_stem}ない",
            "polite_negative": f"{polite_stem}ません",
            "plain_negative_past": f"{negative_stem}なかった",
            "polite_negative_past": f"{polite_stem}ませんでした",
        }

    def _generate_suru(self, dictionary_form: str) -> dict[str, str]:
        if not dictionary_form.endswith("する"):
            raise JapaneseVerbConjugationError("Suru verbs should end with する.")
        base = dictionary_form[:-2]
        stem = f"{base}し"
        return {
            "plain_nonpast": dictionary_form,
            "polite_nonpast": f"{stem}ます",
            "plain_past": f"{stem}た",
            "polite_past": f"{stem}ました",
            "plain_negative": f"{stem}ない",
            "polite_negative": f"{stem}ません",
            "plain_negative_past": f"{stem}なかった",
            "polite_negative_past": f"{stem}ませんでした",
        }

    def _generate_kuru(self, dictionary_form: str) -> dict[str, str]:
        if dictionary_form == "くる":
            return {
                "plain_nonpast": "くる",
                "polite_nonpast": "きます",
                "plain_past": "きた",
                "polite_past": "きました",
                "plain_negative": "こない",
                "polite_negative": "きません",
                "plain_negative_past": "こなかった",
                "polite_negative_past": "きませんでした",
            }
        if dictionary_form == "来る":
            return {
                "plain_nonpast": "来る",
                "polite_nonpast": "来ます",
                "plain_past": "来た",
                "polite_past": "来ました",
                "plain_negative": "来ない",
                "polite_negative": "来ません",
                "plain_negative_past": "来なかった",
                "polite_negative_past": "来ませんでした",
            }
        raise JapaneseVerbConjugationError("Kuru verb should be 来る or くる.")
