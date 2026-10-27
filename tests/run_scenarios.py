"""اختبار جودة قرارات الوكيل. بيحتاج الباك شغال على المنفذ 8000."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.nodes.helpers import is_valid_statement

BASE = "http://localhost:8000"
results = []


def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req, timeout=180)


def new_project():
    return json.load(post("/projects", {"domain": "financial"}))["project_id"]


def chat(pid, message="", action="message"):
    resp = post("/chat/stream", {"project_id": pid, "message": message, "user_action": action})
    event, result, kinds = None, None, []
    for raw in resp:
        line = raw.decode().strip()
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:") and event == "done":
            result = json.loads(line[5:])
        elif line.startswith("data:") and event == "progress":
            kinds.append(json.loads(line[5:]).get("kind"))
        elif line.startswith("data:") and event == "error":
            raise RuntimeError(line)
    result["_kinds"] = kinds
    return result


def check(name, condition, info=""):
    print(("PASS" if condition else "FAIL"), "-", name, info)
    results.append(condition)


print("\n[1] مشكلة غامضة: لازم يسأل سؤال")
pid = new_project()
r = chat(pid, "I want to increase my company profits")
check("decision is ask", r["decision"] == "ask", r["decision"])
check("only one question mark", r["response"].count("?") == 1, r["response"])

print("\n[2] مشكلة واضحة بالكامل: لازم يصيغ مباشرة بدون أسئلة")
pid = new_project()
r = chat(pid, "We are a 20 person software company, profits dropped 15 percent this year because customers are leaving")
check("decision is draft", r["decision"] == "draft", r["decision"])
check("no questions asked", r["questions_asked"] == 0)
check("status is draft", r["statement_status"] == "draft")
check("no confirm sentence inside statement", "please confirm" not in r["statement"].lower())

print("\n[3] المستخدم بده يكمل بدون جواب: افتراضات موضحة")
pid = new_project()
chat(pid, "I want to increase my company profits")
r = chat(pid, "just continue please", "proceed")
check("decision is draft", r["decision"] == "draft", r["decision"])
check("assumptions listed", len(r["assumptions"]) > 0, str(r["assumptions"]))

print("\n[4] حد أقصى للأسئلة: ما يضل يسأل للأبد")
pid = new_project()
r = chat(pid, "I want to grow my business")
asked = [r["response"]] if r["decision"] == "ask" else []
for answer in ["not sure", "I do not know", "no idea"]:
    r = chat(pid, answer)
    if r["decision"] == "ask":
        asked.append(r["response"])
check("stopped asking after max questions and drafted", r["decision"] == "draft", r["decision"])
check("questions_asked <= 3", r["questions_asked"] <= 3, str(r["questions_asked"]))
check("no repeated question", len({q.strip().lower() for q in asked}) == len(asked), str(asked))

print("\n[5] تعديل ثم تأكيد")
pid = new_project()
chat(pid, "We are a 20 person software company, profits dropped 15 percent this year because customers are leaving")
r = chat(pid, "Make it shorter", "edit")
check("edit re-evaluates (draft or ask, not revise)", r["decision"] in ("draft", "ask"), r["decision"])
check("still draft after edit", r["statement_status"] == "draft")
r = chat(pid, "", "confirm")
check("status confirmed", r["statement_status"] == "confirmed", r["statement_status"])
check("pipeline ended at risks", r["decision"] == "risks", r["decision"])
check("plan is not empty", bool(r["plan"].strip()))
check("risks is not empty", bool(r["risks"].strip()))

print("\n[6] تعديلات متتالية: لازم يضل البيان 3 أجزاء")
pid = new_project()
chat(pid, "We are a 20 person software company, profits dropped 15 percent this year because customers are leaving")
chat(pid, "Make it one sentence", "edit")
r = chat(pid, "Add that the drop started after a competitor launched", "edit")
check("statement still has 3 real parts", is_valid_statement(r["statement"]), r["statement"])
check("competitor mentioned", "competitor" in r["statement"].lower())

print("\n[7] اللغة العربية: الرد والبيان بالعربي")
has_arabic = lambda t: any("\u0600" <= c <= "\u06FF" for c in t)
pid = new_project()
r = chat(pid, "بدي زيد أرباح شركتي")
check("arabic question", r["decision"] == "ask" and has_arabic(r["response"]), r["response"])
pid = new_project()
r = chat(pid, "عندي شركة برمجيات فيها 20 موظف والأرباح نزلت 15 بالمية هالسنة لأنو الزبائن عم يتركونا")
check("arabic statement", r["decision"] == "draft" and has_arabic(r["statement"]), r["statement"])
r = chat(pid, "", "confirm")
check("arabic confirm message", has_arabic(r["response"]), r["response"])

print("\n[8] الـ agent بيفهم كلام عادي: كمّل واكتب البيان")
pid = new_project()
chat(pid, "I want to grow my business")
r = chat(pid, "just write the statement now please")
check("agent chose draft from plain text", r["decision"] == "draft", r["decision"])

print("\n[9] التعديل بيرجع لبداية التقييم قبل الـ agent")
pid = new_project()
chat(pid, "We are a 20 person software company, profits dropped 15 percent this year because customers are leaving")
r = chat(pid, "Make it shorter", "edit")
k = r["_kinds"]
check("assessment ran before the agent", "assessment" in k and "agent" in k and k.index("assessment") < k.index("agent"), str(k))
check("no revise step anymore", "revise" not in k, str(k))

PROBLEM = "We are a 20 person software company, profits dropped 15 percent this year because customers are leaving"

print("\n[10] بعد التأكيد: خطة ثم مخاطر، والتقييم بيتخطّى")
pid = new_project()
chat(pid, PROBLEM)
r = chat(pid, "", "confirm")
k = r["_kinds"]
check("plan runs before risks", "plan" in k and "risks" in k and k.index("plan") < k.index("risks"), str(k))
check("assessment model call skipped", "thinking" not in k, str(k))

print("\n[11] متابعة بدون تأكيد: خطة مع بقاء البيان غير معتمد")
pid = new_project()
chat(pid, PROBLEM)
r = chat(pid, "", "proceed")
check("statement stays unconfirmed", r["statement_status"] == "unconfirmed", r["statement_status"])
check("plan still generated", bool(r["plan"].strip()))

print(f"\n=== {sum(results)} / {len(results)} passed ===")
