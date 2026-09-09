"""Offline Stage 14 debug CLI: structured route/evidence only, no answer prose."""
import argparse,json,sqlite3
from datetime import datetime
from pydantic import ValidationError
from intelligence.query.models import QueryRequest
from intelligence.query.resolution import page
from intelligence.query.service import query

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question',required=True)
    parser.add_argument('--page-context')
    parser.add_argument('--as-of',help='Timezone-aware ISO timestamp; required for relative dates.')
    parser.add_argument('--limit',type=int,default=10)
    args=parser.parse_args(argv)
    try:
        request=QueryRequest(question=args.question,page_context=page(args.page_context) if args.page_context else None,as_of=datetime.fromisoformat(args.as_of) if args.as_of else None,limit=args.limit)
        response=query(request)
        print(response.model_dump_json(indent=2))
        return 0
    except (ValueError,ValidationError,sqlite3.Error):
        print(json.dumps({'status':'UNSUPPORTED','reason_code':'INVALID_REQUEST_OR_DATASTORE'}))
        return 1

if __name__=='__main__':raise SystemExit(main())
