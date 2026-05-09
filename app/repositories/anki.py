import json
from datetime import date, datetime

from app.core.database import execute, fetch_all, fetch_one, is_mssql_backend, select_limit_clause
from app.models.anki import AnkiDailySnapshot


class AnkiSnapshotRepository:
    def upsert_daily_snapshot(self, snapshot: AnkiDailySnapshot) -> AnkiDailySnapshot:
        if is_mssql_backend():
            execute(
                """
                MERGE anki_daily_snapshots AS target
                USING (
                    SELECT
                        ? AS id,
                        ? AS snapshot_date,
                        ? AS scope,
                        ? AS reviews,
                        ? AS accuracy,
                        ? AS again_count,
                        ? AS hard_count,
                        ? AS good_count,
                        ? AS easy_count,
                        ? AS non_again_rate,
                        ? AS due_count,
                        ? AS new_due_count,
                        ? AS learn_due_count,
                        ? AS review_due_count,
                        ? AS difficult_cards,
                        ? AS decks,
                        ? AS imported_at
                ) AS source
                ON target.snapshot_date = source.snapshot_date
                WHEN MATCHED THEN
                    UPDATE SET
                        scope = source.scope,
                        reviews = source.reviews,
                        accuracy = source.accuracy,
                        again_count = source.again_count,
                        hard_count = source.hard_count,
                        good_count = source.good_count,
                        easy_count = source.easy_count,
                        non_again_rate = source.non_again_rate,
                        due_count = source.due_count,
                        new_due_count = source.new_due_count,
                        learn_due_count = source.learn_due_count,
                        review_due_count = source.review_due_count,
                        difficult_cards = source.difficult_cards,
                        decks = source.decks,
                        imported_at = source.imported_at
                WHEN NOT MATCHED THEN
                    INSERT (
                        id, snapshot_date, scope, reviews, accuracy, again_count,
                        hard_count, good_count, easy_count, non_again_rate,
                        due_count, new_due_count, learn_due_count, review_due_count,
                        difficult_cards, decks, imported_at
                    )
                    VALUES (
                        source.id,
                        source.snapshot_date,
                        source.scope,
                        source.reviews,
                        source.accuracy,
                        source.again_count,
                        source.hard_count,
                        source.good_count,
                        source.easy_count,
                        source.non_again_rate,
                        source.due_count,
                        source.new_due_count,
                        source.learn_due_count,
                        source.review_due_count,
                        source.difficult_cards,
                        source.decks,
                        source.imported_at
                    );
                """,
                self._snapshot_params(snapshot),
            )
        else:
            execute(
                """
                INSERT INTO anki_daily_snapshots (
                    id, snapshot_date, scope, reviews, accuracy, again_count,
                    hard_count, good_count, easy_count, non_again_rate,
                    due_count, new_due_count, learn_due_count, review_due_count,
                    difficult_cards, decks, imported_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_date) DO UPDATE SET
                    scope = excluded.scope,
                    reviews = excluded.reviews,
                    accuracy = excluded.accuracy,
                    again_count = excluded.again_count,
                    hard_count = excluded.hard_count,
                    good_count = excluded.good_count,
                    easy_count = excluded.easy_count,
                    non_again_rate = excluded.non_again_rate,
                    due_count = excluded.due_count,
                    new_due_count = excluded.new_due_count,
                    learn_due_count = excluded.learn_due_count,
                    review_due_count = excluded.review_due_count,
                    difficult_cards = excluded.difficult_cards,
                    decks = excluded.decks,
                    imported_at = excluded.imported_at
                """,
                self._snapshot_params(snapshot),
            )
        return self.get_snapshot_for_date(snapshot.snapshot_date) or snapshot

    def get_snapshot_for_date(self, target_date: date) -> AnkiDailySnapshot | None:
        row = fetch_one(
            """
            SELECT * FROM anki_daily_snapshots
            WHERE snapshot_date = ?
            """,
            (target_date.isoformat(),),
        )
        if row is None:
            return None
        return self._row_to_snapshot(row)

    def list_recent_snapshots(self, days: int = 7, end_date: date | None = None) -> list[AnkiDailySnapshot]:
        limit_clause = select_limit_clause(days)
        if end_date is not None:
            query = f"""
                SELECT {limit_clause}* FROM anki_daily_snapshots
                WHERE snapshot_date <= ?
                ORDER BY snapshot_date DESC
            """
            rows = (
                fetch_all(query, (end_date.isoformat(),))
                if limit_clause
                else fetch_all(f"{query}\nLIMIT ?", (end_date.isoformat(), days))
            )
        else:
            query = f"""
                SELECT {limit_clause}* FROM anki_daily_snapshots
                ORDER BY snapshot_date DESC
            """
            rows = fetch_all(query) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (days,))
        return [self._row_to_snapshot(row) for row in rows]

    def _snapshot_params(self, snapshot: AnkiDailySnapshot) -> tuple[object, ...]:
        return (
            snapshot.id,
            snapshot.snapshot_date.isoformat(),
            snapshot.scope,
            snapshot.reviews,
            snapshot.accuracy,
            snapshot.again_count,
            snapshot.hard_count,
            snapshot.good_count,
            snapshot.easy_count,
            snapshot.non_again_rate,
            snapshot.due_count,
            snapshot.new_due_count,
            snapshot.learn_due_count,
            snapshot.review_due_count,
            json.dumps(snapshot.difficult_cards, ensure_ascii=False),
            json.dumps(snapshot.decks, ensure_ascii=False),
            snapshot.imported_at.isoformat(),
        )

    def _row_to_snapshot(self, row) -> AnkiDailySnapshot:
        return AnkiDailySnapshot(
            id=row["id"],
            snapshot_date=date.fromisoformat(row["snapshot_date"]),
            scope=row.get("scope", "all_decks"),
            reviews=row["reviews"],
            accuracy=row["accuracy"],
            again_count=row.get("again_count", 0),
            hard_count=row.get("hard_count", 0),
            good_count=row.get("good_count", 0),
            easy_count=row.get("easy_count", 0),
            non_again_rate=row.get("non_again_rate"),
            due_count=row.get("due_count", 0),
            new_due_count=row.get("new_due_count", 0),
            learn_due_count=row.get("learn_due_count", 0),
            review_due_count=row.get("review_due_count", 0),
            difficult_cards=json.loads(row["difficult_cards"]),
            decks=json.loads(row["decks"]),
            imported_at=datetime.fromisoformat(row["imported_at"]),
        )
