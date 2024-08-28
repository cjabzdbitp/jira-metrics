from datetime import datetime, timedelta
import re
import base64
import requests as r
from jira import JIRA
import jira.client
from auth import EMAIL, TOKEN, BASE_URL


AUTHORIZATION_HEADER = base64.b64encode((EMAIL + ":" + TOKEN).encode("ascii")).decode('ascii')
JIRA_CLIENT = JIRA(server=BASE_URL, basic_auth=(EMAIL, TOKEN))

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class JiraIssue:

    def __init__(self, jira_issue: jira.client.Issue):
        self.jira_issue = jira_issue
        self.raw = jira_issue.raw
        self.summary = jira_issue.fields.summary
        self.key = jira_issue.key
        self.issue_type = self.raw["fields"]["issuetype"]["name"]
        self.created = datetime.strptime(self.raw["fields"]["created"][:-9], TIME_FORMAT)
        self.changelog = self.raw["changelog"]["histories"]
        self.changelog.reverse()  # now starts from the beginning
        self.linked_pi_up_issues = list(set(re.findall("'key': '(UP-\d\d\d|PI-\d\d\d)", str(self.raw))))
        self.project = self.key.split("-")[0]
        self.story_points_field = "customfield_10020"
        self.story_points = 0 if self.raw["fields"][self.story_points_field] is None else self.raw["fields"][self.story_points_field]
        self.sprints_field = "customfield_10016"
        self.sprint_ids = \
            [] if self.raw["fields"][self.sprints_field] is None \
            else [sprint["id"] for sprint in self.raw["fields"][self.sprints_field]]
        self.time_in_statuses = None
        self.development_time = None

    def find_all_sprints_from_changelog(self):
        """Return all sprint ids where the issue presented, even if it was removed from it (searching the changelog)."""
        self.all_sprint_ids = set()
        for log in self.changelog:
            for item in log["items"]:
                if item["field"] == "Sprint":
                    if item["to"].isdigit():
                        self.all_sprint_ids.add(item["to"])
                    elif item["to"] == "":
                        pass
                    else:
                        self.all_sprint_ids.update(item["to"].split(", "))

                    if item["from"].isdigit():
                        self.all_sprint_ids.add(item["from"])
                    elif item["from"] == "":
                        pass
                    else:
                        self.all_sprint_ids.update(item["from"].split(", "))
        return self.all_sprint_ids

    def count_time_in_all_statuses(self):

        # find all statuses where issue was
        statuses = set()
        for log in self.changelog:
            for i in log["items"]:
                if i["field"] == 'status':
                    statuses.add(i["fromString"])
                    statuses.add(i["toString"])

        # count time in each status
        self.time_in_statuses = {status: timedelta() for status in statuses}
        i = 0  # need it to separate logic when find the first status change
        for log in self.changelog:
            for item in log["items"]:
                if item["field"] == 'status':
                    if i == 0:
                        # first status change
                        last_change_status_time = datetime.strptime(log["created"][:-9], TIME_FORMAT)
                        self.time_in_statuses[item["fromString"]] = last_change_status_time - self.created
                        i += 1
                        continue
                    status_changed_time = datetime.strptime(log["created"][:-9], TIME_FORMAT)
                    delta = status_changed_time - last_change_status_time
                    self.time_in_statuses[item["fromString"]] += delta
                    last_change_status_time = status_changed_time

        from_created_to_done = timedelta(0)
        for i in self.time_in_statuses.items():
            from_created_to_done += i[1]

    def count_development_time(self):
        if self.time_in_statuses is None:
            self.count_time_in_all_statuses()

        in_review_statuses = ["In Review"]
        cycle_time_statuses = in_review_statuses + \
            ["In Progress", "Product Review", "PO Review", "Ready for testing", "Testing", "Ready for Deploy"]
        lead_time_statuses = cycle_time_statuses + ["To Do", "New", "Analyze"]
        all_statuses = lead_time_statuses + ["Done"]

        self.development_time = {"lead time": timedelta(), "cycle time": timedelta(), "in review": timedelta()}

        for status, time in self.time_in_statuses.items():
            if status in lead_time_statuses:
                self.development_time["lead time"] += time
            if status in cycle_time_statuses:
                self.development_time["cycle time"] += time
            if status in in_review_statuses:
                self.development_time["in review"] += time

        # check that we don't miss any status in stats
        for status in self.time_in_statuses.keys():
            if status not in all_statuses:
                raise ValueError(f"!!! {self.key}: was in status {status}, but we missed it when count time in statuses")


class JiraSprint:

    def __init__(self, sprint_id: str):
        self.sprint_id = sprint_id
        self.data = r.get(
            url=f"{BASE_URL}/rest/agile/1.0/sprint/{sprint_id}",
            headers={"Authorization": f"Basic {AUTHORIZATION_HEADER}"}
        ).json()
        self.name = self.data["name"]
        self.board_id = self.data["originBoardId"]
        self.start = self.data["startDate"].split("T")
        self.start = "'" + self.start[0] + " " + self.start[1][:-8] + "'"
        self.end = self.data["completeDate"].split("T")
        self.end = "'" + self.end[0] + " " + self.end[1][:-8] + "'"


def get_jira_issues_by_jql(jql: str, jira_client: jira.client.JIRA, start_at=0):
    """Returns list of custom JiraIssue class objects. Jira API cannot return more than 100 issues at once,
    so we need to iterate until we get less than 100 issues in response."""
    i = start_at
    issues = []
    while True:
        issues_i = jira_client.search_issues(jql_str=jql, expand="changelog", maxResults=100, startAt=i)
        for issue in issues_i:
            issues.append(JiraIssue(issue))
        i += 100
        if len(issues_i) < 100:
            break
    return issues


def get_all_issues_in_project(project_id: str):
    return get_jira_issues_by_jql(f"project = {project_id}", JIRA_CLIENT)


def get_all_issues_from_sprint_greenhopper(sprint_id: str, board_id: str):
    """Get all issues appeared in sprint according to Greenhopper log"""
    gh = r.get(
        url=f"{BASE_URL}/rest/greenhopper/1.0/rapid/charts/scopechangeburndownchart?rapidViewId={board_id}&sprintId={sprint_id}",
        headers={"Authorization": f"Basic {AUTHORIZATION_HEADER}"}).json()
    keys = set(value[0]["key"] for (key, value) in gh["changes"].items())
    issues = get_jira_issues_by_jql(f"issue in ({tuple(keys)})", JIRA_CLIENT)
    return issues