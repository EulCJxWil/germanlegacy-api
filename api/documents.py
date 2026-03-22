from http.server import BaseHTTPRequestHandler
import json
import os
import pathlib
import anthropic

LAW_DIR = pathlib.Path(__file__).parent.parent / 'law'
DOCUMENTS_MD = (LAW_DIR / 'documents.md').read_text()
KNOWLEDGE_BASE = (LAW_DIR / 'knowledge-base.md').read_text()

SYSTEM_PROMPT = """You are a German citizenship document specialist. A user has completed an eligibility checker and you must produce a precise, actionable document checklist tailored to their specific case.

Follow these steps:

1. Identify the pathway from the case summary (Feststellung, StAG §5, Art. 116 GG, StAG §15, or paternity).
2. Using DOCUMENTS.MD, list the pathway-specific documents required for the German ancestor.
3. For each generation in the chain between the ancestor and the applicant, list the per-generation documents (birth record + marriage record, or note if parents were not married).
4. List the per-applicant documents for the applicant themselves.
5. Apply the FBI background check rule from DOCUMENTS.MD — include it only if the pathway requires it.
6. Add any relevant practical notes from KNOWLEDGE-BASE.MD (certified copies, how to get missing documents, USCIS records, etc.).

Format the output as a numbered list grouped by section (e.g. "Ancestor documents", "Generation 1 documents", "Your documents", "Notes"). Be specific — name each document. Do not add disclaimers or suggest consulting an attorney.

---
DOCUMENTS.MD:
""" + DOCUMENTS_MD + """

---
KNOWLEDGE-BASE.MD:
""" + KNOWLEDGE_BASE


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))
        case_summary = body.get('caseSummary', '').strip()

        if not case_summary:
            self._respond(400, {'error': 'caseSummary required'})
            return

        try:
            client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
            message = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{
                    'role': 'user',
                    'content': f"Case summary:\n{case_summary}"
                }]
            )
            self._respond(200, {'result': message.content[0].text})
        except Exception as e:
            self._respond(500, {'error': str(e)})

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self._cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
