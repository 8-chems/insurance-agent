import re


def render(answer: str, ledger: dict):
    order, sources = {}, []

    def sub(m):
        sid = m.group(1)
        if sid not in ledger:
            return ""
        if sid not in order:
            order[sid] = len(order) + 1
            e = ledger[sid]
            sources.append({"citation_id": str(order[sid]), "type": e.kind, "title": e.title,
                            "version": e.version, "section": e.section, "page": e.page,
                            "record": sid if e.kind == "api" else None,
                            "retrieved_at": e.retrieved_at})
        return f"[{order[sid]}]"

    return re.sub(r"\[([^\]]+)\]", sub, answer), sources
