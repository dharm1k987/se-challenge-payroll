import re
from collections import OrderedDict
from datetime import datetime

from db import db_crud


def read_csv(file_handler, con):

  filename = file_handler.filename
  report_num = re.findall(r"time-report-(\d+)\.csv",filename)

  if not report_num:
    return 500, f"Either {filename} is not a csv, or it does not follow naming convention"

  report_num = report_num[0]
  if db_crud.exists_report(con, report_num):
    return 409, f"Report num {report_num} exists. Cannot reuse."

  line_count = 0
  for row in file_handler.readlines():
    date, hours, employee, job = row.decode("utf-8").strip().split(",")
    if line_count == 0:
      print(f'Column names are {row}')
    else:
      try:
        db_crud.insert_csv_row(con, date, hours, employee, job, report_num)
      except Exception as e:
        return 500, e.args[0]

    line_count += 1
  return 200, f"File {filename} uploaded successfully"

def generate_report(con):
  try:
    rows = db_crud.get_records_sorted(con)
  except Exception as e:
    return 500, e.args[0]

  employeeReports = OrderedDict()

  for emp_id, timestamp, earnings in rows:
    report = OrderedDict()
    report["employeeId"] = int(emp_id)
    amountPaid = f"${earnings}"
    payPeriod = calculatePeriod(timestamp)

    # see if we can merge this with another entry
    key = f"{emp_id}-{payPeriod['endDate']}"
    if key in employeeReports:
      # update the earnings
      currentEarnings = float(employeeReports[key]["amountPaid"][1:])
      employeeReports[key]["amountPaid"] = f"${currentEarnings + float(earnings)}"
    else:
      report["payPeriod"] = payPeriod
      report["amountPaid"] = amountPaid
      employeeReports[key] = report

  employeeReportsList = [employeeReports[key] for key in employeeReports]
  res = OrderedDict()
  res["payrollReport"] = {}
  res["payrollReport"]["employeeReports"] = employeeReportsList

  return 200, res

def calculatePeriod(timestamp):
  NUM_DAYS_PER_MONTH = {1:31, 2:28, 3:31, 4:3, 5:31, 6:30,
                        7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
  dt = datetime.fromtimestamp(timestamp)
  month, day, year = dt.month, dt.day, dt.year
  dates = OrderedDict()
  num_days = NUM_DAYS_PER_MONTH[dt.month]
  mid_day = 15
  if dt.day <= mid_day:
    # pay is for first half
    startDate = f"{year}-{month}-01"
    endDate = f"{year}-{month}-{mid_day}"
  else:
    # pay is for last half
    startDate = f"{year}-{month}-{mid_day + 1}"
    endDate = f"{year}-{month}-{num_days}"

  dates["startDate"] = startDate
  dates["endDate"] = endDate
  return dates

def create_login(con, username, password):
  try:
    rows = db_crud.create_user(con, username, password)
    return 200, f"Successfully created user {username}"
  except Exception as e:
    return 500, e.args[0]

def check_login(con, username, password):
  try:
    id = db_crud.check_user(con, username, password)
    if not id:
      return 401, "User does not exist or password is incorrect", -1
    return 200, f"Successfully logged in for user {username}", id
  except Exception as e:
    return 500, e.args[0], -1
