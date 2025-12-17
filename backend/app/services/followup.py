from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.task import Task

async def build_followup_text(db: AsyncSession, slot: str) -> str:
    today = date.today()

    due_today = (await db.execute(select(Task).where(Task.due_date == today, Task.status != "done"))).scalars().all()
    overdue = (await db.execute(select(Task).where(and_(Task.due_date < today, Task.due_date.is_not(None), Task.status != "done")))).scalars().all()
    doing = (await db.execute(select(Task).where(Task.status == "doing"))).scalars().all()

    lines = [f"[{slot}] フォロー"]
    if slot == "morning":
        if overdue: lines.append(f"- 期限切れ: {len(overdue)}件")
        if due_today: lines.append(f"- 今日期限: {len(due_today)}件")
        if doing: lines.append(f"- Doing: {len(doing)}件")
        lines.append("- 今日の最優先を1つ選ぶ？（/tasks から urgent/high を見るのがおすすめ）")
    elif slot == "noon":
        lines.append("- 昼チェック：止まってるタスクがあれば、次の一手を小さく切る")
        if due_today: lines.append(f"- 今日期限（未完了）: {len(due_today)}件")
    else:
        lines.append("- 夕チェック：未完了の回収と、明日の頭出し")
        if due_today: lines.append(f"- 今日期限（未完了）: {len(due_today)}件")

    return "\n".join(lines)
