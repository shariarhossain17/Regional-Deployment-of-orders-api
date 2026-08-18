import csv
import io
import os
import time
from datetime import datetime, timezone

import boto3
import pg8000

s3 = boto3.client("s3")
ses = boto3.client("ses")


def handler(event, context):
    t0 = time.time()
    token = os.environ["STUDENT_TOKEN"]
    nonce = os.environ.get("SESSION_NONCE") or "pre-session"
    bucket = os.environ["DUMP_BUCKET"]

    conn = pg8000.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        timeout=10,
    )
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM orders")
        n = int(cur.fetchone()[0])
        cur.execute(
            "SELECT id, customer, amount_cents, status, created_at "
            "FROM orders ORDER BY id"
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "customer", "amount_cents", "status", "created_at"])
    writer.writerows(rows)
    body = buf.getvalue().encode("utf-8")

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"{token}/{day}-{token}.csv"
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/csv")

    ms = int((time.time() - t0) * 1000)
    line = f"rows={n} dump_size={len(body)} duration_ms={ms} key={key}"
    print(line)

    ses.send_email(
        Source=os.environ["SES_FROM"],
        Destination={"ToAddresses": [os.environ["SES_TO"]]},
        Message={
            "Subject": {"Data": f"[{nonce}] orders-api dump {token}"},
            "Body": {"Text": {"Data": line}},
        },
    )
    return {"ok": True, "summary": line}
