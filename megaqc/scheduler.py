
from flask import current_app
from megaqc.model.models import Upload
from megaqc.user.models import User
from megaqc.extensions import db
from megaqc.api.utils import handle_report_data
from flask_apscheduler import APScheduler
from io import BufferedReader

import json
import datetime
import os
import gzip

scheduler = APScheduler()

def init_scheduler(app):
    scheduler.init_app(app)
    scheduler.start()

def upload_reports_job():
    with scheduler.app.app_context():
        queued_uploads = db.session.query(Upload).filter(Upload.status == "NOT TREATED").all()
        for row in queued_uploads:
            row.status = "IN TREATMENT"
            db.session.add(row)
            db.session.commit()
            user = db.session.query(User).filter(User.user_id == row.user_id).one()
            # Check if we have a gzipped file
            gzipped = False
            with open(row.path, 'r') as fh:
                # Check if we have a gzipped file
                file_start = fh.read(3)
                if file_start == "\x1f\x8b\x08":
                    gzipped = True
            try:
                if gzipped:
                    with BufferedReader(gzip.open(row.path, 'rb')) as fh:
                        data = json.load(fh)
                else:
                    with open(row.path, 'r') as fh:
                        data = json.load(fh)
                # Now save the parsed JSON data to the database
                ret = handle_report_data(user, data)
            except Exception as e:
                ret = (False, str(e))
            if ret[0]:
                row.status = "TREATED"
                row.message = "The document has been uploaded successfully"
                os.remove(row.path)
            else:
                row.status = "FAILED"
                row.message = "The document has not been uploaded : {0}".format(ret[1])
            row.modified_at = datetime.datetime.utcnow()
            db.session.add(row)
            db.session.commit()
