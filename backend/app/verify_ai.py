"""Opt-in live provider check using the fictional supplied data, with no DB writes."""
import argparse
import json
from . import ai
from .config import settings, BACKEND_DIR
from .schemas import Category


def sample_context():
    source = json.loads((BACKEND_DIR / 'data' / 'authorcare_sample_data.json').read_text(encoding='utf-8'))
    author = source['authors'][0]
    book = dict(author['books'][0])
    book.pop('book_id', None)
    category = Category.royalty.value
    return {
        'kb_version': ai.KB['version'], 'company': ai.KB['company'], 'tone': ai.KB['tone'],
        'policies': {category: ai.KB['sections'][category]},
        'examples': [e for e in ai.KB['examples'] if e['category'] == category][:2],
        'author_first_name': author['name'].split()[0],
        'account_pending_royalty': sum(b['royalty_pending'] for b in author['books']),
        'recorded_book': book,
        'ticket': {'subject': 'Please verify my unpaid royalties',
                   'description': 'I have not received royalties for six months. Please check the payment status.',
                   'category': category, 'priority': 'High'},
        'recent_public_messages': [], 'attachments': [], 'attachment_contents_available_to_model': False,
        'unavailable_facts': ['bank verification', 'quarterly sales ledger', 'verified due date'],
        'completed_external_actions': [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Send two live OpenAI requests; usage is billed to your API account.')
    args = parser.parse_args()
    if not args.run:
        parser.print_help()
        return 0
    if not settings.openai_api_key.strip():
        print('FAIL: set OPENAI_API_KEY in the project .env, then retry. Do not paste your key into chat.')
        return 1
    context = sample_context()
    triage = ai.classify(context['ticket']['subject'], context['ticket']['description'])
    draft = ai.generate_draft(context)
    report = {
        'model': settings.openai_model,
        'triage': {'source': triage.source, **triage.result.model_dump(), 'error': triage.error},
        'draft': {'source': draft.source, **draft.result.model_dump(), 'error': draft.error},
        'tokens': {'input': triage.input_tokens + draft.input_tokens, 'output': triage.output_tokens + draft.output_tokens},
        'manual_review': 'Confirm policy accuracy, missing-fact handling and tone; successful API calls do not certify model quality.',
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))
    passed = triage.source == draft.source == 'llm'
    passed = passed and triage.result.category == Category.royalty and triage.result.priority.value == 'High'
    print('PASS: both live calls succeeded and the sample triage matched expectations.' if passed
          else 'FAIL: a provider call fell back or the sample category/priority needs review. See the safe error above.')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
