# Патч копии контента для QA (XSS-нагрузки + доп. экспертизы). Запуск: python tests/qa/qa_patch_content.py <корень КОПИИ репозитория>
import sys, yaml, pathlib
root = pathlib.Path(sys.argv[1]) / "content"
X = lambda tag: f'<img src=x onerror=alert("{tag}")><script>alert("{tag}-s")</script>'
def load(p): return yaml.safe_load((root/p).read_text(encoding="utf-8"))
def dump(p, d): (root/p).write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")

st = load("stages.yaml")
s1 = st["stages"][0]
s1["intro"] = s1["intro"] + "\n\n" + X("INTRO")
q1 = s1["questions"][0]
q1["prompt"] += X("PROMPT")
q1["hints"][0] += X("HINT1")
q1["fields"][0]["label"] += X("LABEL")
q2 = s1["questions"][1]
q2["items"][0]["text"] += X("ORDER")
q2["hints"] = [h + X(f"HINTO{i}") for i, h in enumerate(q2["hints"])]
b1 = s1["questions"][2]
b1["prompt"] += X("BONUSPROMPT")
s2b1 = [q for q in st["stages"][1]["questions"] if q["id"] == "b1"][0]
s2b1["options"][0]["text"] += X("OPTION")
dump("stages.yaml", st)

g = load("pages/gromov/page.yaml")
g["posts"][0]["text"] += X("POST")
g["posts"][0]["geo"] += X("GEO")
g["posts"][0]["comments"] = [{"author": "Гость" + X("CAUTHOR"), "text": "Коммент" + X("COMMENT")}]
g["profile"]["position"] += X("POSITION")
dump("pages/gromov/page.yaml", g)

n = load("pages/news/page.yaml")
n["article"]["headline"] += X("HEADLINE")
n["comments"] = [{"author": "Читатель" + X("NAUTHOR"), "datetime": "2026-11-11T10:00", "text": "Текст" + X("NCOMMENT")}]
n["sidebar"] = [{"title": "Новость" + X("SIDEBAR"), "datetime": "2026-11-11T08:00"}]
n["ads"] = [{"title": "Баннер" + X("ADT"), "text": "Реклама" + X("AD")}]
dump("pages/news/page.yaml", n)

c = load("pages/cloud/page.yaml")
c["folders"][0]["rows"][1][4] = "Комментарий" + X("REGISTRY")
c["folders"][0]["rows"][1][1] = "Лот" + X("LOT")
c["folders"][0]["title"] += X("FOLDER")
c["account"] = "login" + X("ACCOUNT")
c["password"] = "qa-pass-1"
dump("pages/cloud/page.yaml", c)

i = load("pages/inna/page.yaml")
i["posts"][0]["caption"] = "Новая красота" + X("CAPTION")
i["profile"]["bio"] = "О себе" + X("BIO")
dump("pages/inna/page.yaml", i)

ph = load("pages/pharma/page.yaml")
ph["drugs"][1]["contraindications"] += X("CONTRA")
ph["drugs"][1]["trade"][0] += X("TRADE")
dump("pages/pharma/page.yaml", ph)

call = load("pages/call/page.yaml")
call["note"] += X("CALLNOTE")
dump("pages/call/page.yaml", call)

e = load("expertise.yaml")
for r in e["results"]:
    if r["id"] == "water-chem":
        r["text"] += X("LABTEXT")
e["results"].append({"id": "qa-water-s3", "object": "water", "types": ["chem"], "stage": 3, "bases": ["1-09", "1-10"], "text": "QA-WATER-STAGE3"})
e["results"].append({"id": "qa-costume-s2", "object": "costume", "types": ["chem"], "stage": 2, "bases": ["1-01"], "text": "QA-COSTUME-STAGE2"})
dump("expertise.yaml", e)

f = load("finale.yaml")
f["fates"][0]["text"] += X("FATE")
dump("finale.yaml", f)

d = load("documents.yaml")
d["documents"][0]["title"] += X("DOCTITLE")
dump("documents.yaml", d)
print("patched")
