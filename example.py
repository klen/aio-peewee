"""Example application

Requirements:
    asgi-tools
    uvicorn

Run the example with uvicorn:

    $ uvicorn --port 5000 example:app

"""

import datetime as dt

from asgi_tools import App
from aiopeewee import PeeweeASGIPlugin
import peewee as pw


db = PeeweeASGIPlugin(url='sqlite+async:///db.sqlite')


@db.register
class Visit(pw.Model):
    created = pw.DateTimeField(default=dt.datetime.utcnow())
    address = pw.CharField()


db.create_tables()


app = App()


@app.route('/')
async def visits_json(request):
    """Store the visit and load latest 10 visits."""
    Visit.create(address=request.client[0])
    return [{
        'id': v.id, 'address': v.address, 'timestamp': round(v.created.timestamp()),
    } for v in Visit.select().order_by(Visit.id.desc()).limit(10)]


app = db.middleware(app)
