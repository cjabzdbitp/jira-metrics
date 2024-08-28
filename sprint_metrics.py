from datetime import datetime
import argparse
import pandas as pd
from my_jira import *
from my_jira import JIRA_CLIENT
from helpers import timedelta_formatter

parser = argparse.ArgumentParser(description="Team sprint metrics. ",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-s", "--sprint", type=str, help="Pass the sprint id")
parser.add_argument("-p", "--project", type=str, help="Pass the project key")
args = parser.parse_args()

PROJECT_ID = args.project
SPRINT_ID = args.sprint

SPRINT = JiraSprint(SPRINT_ID)
print(f"\n{'*' * 100}\n'{PROJECT_ID}' PROJECT STATISTICS FOR SPRINT {SPRINT.sprint_id} '{SPRINT.name}' "
      f"(time: '{str(datetime.now())}):")


def sprint_goals_completion(project: str, sprint_id: str):
    sprint = JiraSprint(sprint_id)
    print(f"\n{'-' * 100}\nSPRINT GOALS COMPLETION:")
    sprint_goals_planned = get_jira_issues_by_jql(
        f"project = {project} and "
        f"sprint = {sprint_id} and "
        f"labels = sprint_goals",
        JIRA_CLIENT
    )
    sprint_goals_completed = get_jira_issues_by_jql(
        f"project = {project} and "
        f"sprint = {sprint_id} and "
        f"labels = sprint_goals and "
        f"resolved >= {sprint.start} and "
        f"resolved < {sprint.end}",
        JIRA_CLIENT
    )

    print(f"{len(sprint_goals_planned)} planned sprint goal(s):")
    for sprint_goal_planned in sprint_goals_planned:
        print(f"    {sprint_goal_planned.key} ({sprint_goal_planned.issue_type}), SP={sprint_goal_planned.story_points} '{sprint_goal_planned.summary}'")

    print(f"{len(sprint_goals_completed)} completed sprint goal(s):")
    for sprint_goal_completed in sprint_goals_completed:
        print(f"    {sprint_goal_completed.key} ({sprint_goal_completed.issue_type}), SP={sprint_goal_completed.story_points} '{sprint_goal_completed.summary}'")


def development_time(project_id: str, sprint_id: str):
    print(f"\n{'-' * 100}\nDEVELOPMENT TIME:")
    sprint = JiraSprint(sprint_id)
    percentile_interpolation = "linear"
    lead_time_jql = \
        f"Project = {project_id} and " \
        f"Sprint = {sprint.sprint_id} and " \
        f"priority in (Critical,High) and " \
        f"type = Story and " \
        f"resolved >= {sprint.start} and " \
        f"resolved < {sprint.end} and " \
        f"statusCategory = Done"
    lead_time_issues = get_jira_issues_by_jql(lead_time_jql, JIRA_CLIENT)
    for issue in lead_time_issues:
        issue.count_development_time()

    lead_time = pd.DataFrame(
        [(issue.key, issue.issue_type, f"{issue.summary[:20]}", issue.development_time["lead time"]) for issue in lead_time_issues],
        columns=["KEY", "TYPE", "SUMMARY", "LEAD_TIME"]
    )
    lead_time.sort_values(by="LEAD_TIME", inplace=True, ascending=False)
    print(f"\nLead time ({lead_time_jql}),\n"
          "50th, 80th, 90th Percentiles:\n",
          timedelta_formatter(lead_time.LEAD_TIME.quantile(.5, interpolation=percentile_interpolation)), "/",
          timedelta_formatter(lead_time.LEAD_TIME.quantile(.8, interpolation=percentile_interpolation)), "/",
          timedelta_formatter(lead_time.LEAD_TIME.quantile(.9, interpolation=percentile_interpolation)), "\n",
          lead_time)

    cycle_and_in_review_time_jql = \
        f"Project = {project_id} and " \
        f"Sprint = {sprint.sprint_id} and " \
        f"resolved >= {sprint.start} and " \
        f"resolved < {sprint.end} and " \
        f"statusCategory = Done"
    cycle_and_in_review_time_issues = get_jira_issues_by_jql(cycle_and_in_review_time_jql, JIRA_CLIENT)
    for issue in cycle_and_in_review_time_issues:
        issue.count_development_time()

    cycle_time = pd.DataFrame(
        [(issue.key, issue.issue_type, f"{issue.summary[:20]}", issue.development_time["cycle time"]) for issue in cycle_and_in_review_time_issues],
        columns=["KEY", "TYPE", "SUMMARY", "CYCLE_TIME"]
    )
    cycle_time.sort_values(by="CYCLE_TIME", inplace=True, ascending=False)
    print(f"\nCycle time ({cycle_and_in_review_time_jql}),\n"
          "50th, 80th, 90th Percentiles:\n",
          timedelta_formatter(cycle_time.CYCLE_TIME.quantile(.5, interpolation=percentile_interpolation)), "/",
          timedelta_formatter(cycle_time.CYCLE_TIME.quantile(.8, interpolation=percentile_interpolation)), "/",
          timedelta_formatter(cycle_time.CYCLE_TIME.quantile(.9, interpolation=percentile_interpolation)), "\n",
          cycle_time)

    in_review_time = pd.DataFrame(
        [(issue.key, issue.issue_type, f"{issue.summary[:20]}", issue.development_time["in review"]) for issue in cycle_and_in_review_time_issues],
        columns=["KEY", "TYPE", "SUMMARY", "IN_REVIEW"]
    )
    in_review_time.sort_values(by="IN_REVIEW", inplace=True, ascending=False)
    print(f"\nIn Review time ({cycle_and_in_review_time_jql}), "
          "50th, 80th, 90th Percentiles:\n",
          timedelta_formatter(in_review_time.IN_REVIEW.quantile(.5, interpolation=percentile_interpolation)), "/",
          timedelta_formatter(in_review_time.IN_REVIEW.quantile(.8, interpolation=percentile_interpolation)), "/",
          timedelta_formatter(in_review_time.IN_REVIEW.quantile(.9, interpolation=percentile_interpolation)), "\n",
          in_review_time)


def team_velocity(project: str, sprint_id: str):
    print(f"\n{'-' * 100}\nTEAM VELOCITY:")
    sprint = JiraSprint(sprint_id)
    issues_committed = get_all_issues_from_sprint_greenhopper(sprint_id, sprint.board_id)
    print("Issues committed: ")
    for issue in issues_committed:
        print(f"    {issue.key} ({issue.issue_type}), SP={issue.story_points} '{issue.summary}'")

    issues_completed_jql = \
        f"project = {project} and " \
        f"sprint = {sprint_id} and " \
        f"resolved >= {sprint.start} and " \
        f"resolved < {sprint.end}"
    issues_completed = get_jira_issues_by_jql(issues_completed_jql, JIRA_CLIENT)
    print("Issues completed: ", issues_completed_jql)
    for issue in issues_completed:
        print(f"    {issue.key} ({issue.issue_type}), SP={issue.story_points} '{issue.summary}'")

    issues_not_completed = [issue for issue in issues_committed if
                            issue.key not in [issue.key for issue in issues_completed]]
    print("Issues not completed: ", )
    for issue in issues_not_completed:
        print(f"    {issue.key} ({issue.issue_type}), SP={issue.story_points} '{issue.summary}'")

    committed_story_points = sum([issue.story_points for issue in issues_committed])
    completed_story_points = sum([issue.story_points for issue in issues_completed])
    print(f"Committed story points: {committed_story_points}")
    print(f"Completed story points: {completed_story_points}")
    if committed_story_points != 0:
        print(f"Completed/committed ratio: {round(completed_story_points / committed_story_points * 100, 2)}%")


def unplanned_work(project: str, sprint_id: str):
    sprint = JiraSprint(sprint_id)
    print(f"\n{'-' * 100}\nUNPLANNED WORK:")
    issues_completed_jql = \
        f"project = {project} and " \
        f"sprint = {sprint_id} and " \
        f"resolved >= {sprint.start} and " \
        f"resolved < {sprint.end}"
    issues_completed = get_jira_issues_by_jql(issues_completed_jql, JIRA_CLIENT)
    issues_unplanned = []
    for issue in issues_completed:
        if issue.linked_pi_up_issues:
            issues_unplanned.append(issue)
            print(f"    Issue {issue.key} ({issue.issue_type}) '{issue.summary}'"
                  f"\n        has linked UP/PI ticket(s): {issue.linked_pi_up_issues}")

    completed_story_points = sum([issue.story_points for issue in issues_completed])
    unplanned_story_points = sum([issue.story_points for issue in issues_unplanned])
    print(f"All completed issues story points: {completed_story_points}")
    print(f"Unplanned work story points: {unplanned_story_points}")
    if completed_story_points != 0:
        print(f"Unplanned/completed ratio: {round(unplanned_story_points / completed_story_points * 100, 2)}%")


def focus_structure(project: str, sprint_id: str):
    sprint = JiraSprint(sprint_id)
    print(f"\n{'-' * 100}\nFOCUS STRUCTURE")

    issues_completed_jql = \
        f"project = {project} and " \
        f"sprint = {sprint_id} and " \
        f"resolved >= {sprint.start} and " \
        f"resolved < {sprint.end}"
    issues_completed = get_jira_issues_by_jql(issues_completed_jql, JIRA_CLIENT)
    completed_story_points = sum([issue.story_points for issue in issues_completed])

    unplanned_issues = []
    for issue in issues_completed:
        if issue.linked_pi_up_issues:
            unplanned_issues.append(issue)
    unplanned_story_points = sum([issue.story_points for issue in unplanned_issues])

    bugs_resolved_jql = \
        f"project = {project} and " \
        f"type = bug and " \
        f"sprint = {sprint_id} and " \
        f"resolved > {sprint.start} and " \
        f"resolved < {sprint.end}"
    bugs_resolved_with_unplanned = get_jira_issues_by_jql(bugs_resolved_jql, JIRA_CLIENT)
    # now let's exclude bugs which are linked to PI or UP tickets, because they are already in Unplanned issues stats
    bugs_resolved = []
    for bug in bugs_resolved_with_unplanned:
        if bug.key not in [unplanned_issue.key for unplanned_issue in unplanned_issues]:
            bugs_resolved.append(bug)

    bugs_resolved_story_points = sum([issue.story_points for issue in bugs_resolved])
    roadmap_completed_jql = \
        f"project = {project} and " \
        f"labels = roadmap and " \
        f"sprint = {sprint_id} and " \
        f"resolved >= {sprint.start} and " \
        f"resolved < {sprint.end}"
    roadmap_completed = get_jira_issues_by_jql(roadmap_completed_jql, JIRA_CLIENT)
    roadmap_completed_story_points = sum([issue.story_points for issue in roadmap_completed])

    tech_debt_closed_jql = \
        f"project = {project} and " \
        f"(labels in (techdebt, tech_debt, tech) or summary ~ 'tech' or summary ~ 'Tech') and " \
        f"sprint = {sprint_id} and " \
        f"resolved >= {sprint.start} and " \
        f"resolved < {sprint.end}"
    tech_debt_closed = get_jira_issues_by_jql(tech_debt_closed_jql, JIRA_CLIENT)
    tech_debt_closed_story_points = sum([issue.story_points for issue in tech_debt_closed])

    other_issues_closed = []
    for issue in issues_completed:
        if issue.key not in set(
            [unplanned_issue.key for unplanned_issue in unplanned_issues] + \
            [bug.key for bug in bugs_resolved] + \
            [tech_debt.key for tech_debt in tech_debt_closed] + \
            [roadmap.key for roadmap in roadmap_completed]
    ):
            other_issues_closed.append(issue)
    other_issues_closed_story_points = sum([issue.story_points for issue in other_issues_closed])

    print(f"All completed issues: {issues_completed_jql} \n    "
          f"count={len(issues_completed)}, SP={completed_story_points}")
    print(f"Unplanned issues: \n    count={len(unplanned_issues)}, SP={unplanned_story_points}")
    for unplanned_issue in unplanned_issues:
        print(f"    Issue {unplanned_issue.key} ({unplanned_issue.issue_type}) '{unplanned_issue.summary}'"
              f"\n          has linked UP/PI ticket(s): {unplanned_issue.linked_pi_up_issues}")

    print(f"Roadmap issues completed: {roadmap_completed_jql} \n    "
          f"count={len(roadmap_completed)}, SP={roadmap_completed_story_points}")
    for roadmap_issue in roadmap_completed:
        print(f"    {roadmap_issue.key} ({roadmap_issue.issue_type}), "
              f"SP={roadmap_issue.story_points} '{roadmap_issue.summary}'")

    print(f"Bugs resolved (without linked to PI or UP): {bugs_resolved_jql} \n"
          f"    count={len(bugs_resolved)}, SP={bugs_resolved_story_points}")
    for bug in bugs_resolved:
        print(f"    {bug.key}, SP={bug.story_points} '{bug.summary}'")

    print(f"Tech debt closed: {tech_debt_closed_jql} \n"
          f"    count={len(tech_debt_closed)}, SP={tech_debt_closed_story_points}")
    for tech_debt in tech_debt_closed:
        print(f"    {tech_debt.key} ({tech_debt.issue_type}), SP={tech_debt.story_points} '{tech_debt.summary}'")

    print(f"Other issues closed: \n    count={len(other_issues_closed)}, SP={other_issues_closed_story_points}")
    for issue in other_issues_closed:
        print(f"    {issue.key} ({issue.issue_type}), SP={issue.story_points} '{issue.summary}'")


def defect_dynamics(project: str):
    print(f"\n{'-' * 100}\nDEFECT DYNAMICS:")
    bugs_closed = get_jira_issues_by_jql(
        f"project = {project} and "
        f"type = bug and "
        f"priority != low and "
        f"statusCategory = Done",
        JIRA_CLIENT
    )
    bugs_open = get_jira_issues_by_jql(
        f"project = {project} and "
        f"type = bug and "
        f"priority != low and "
        f"statusCategory != Done",
        JIRA_CLIENT
    )

    print(f"    Closed (Medium+): {len(bugs_closed)}\n"
          f"    Remaining (Medium+): {len(bugs_open)}")


if __name__ == "__main__":
    sprint_goals_completion(PROJECT_ID, SPRINT_ID)
    development_time(PROJECT_ID, SPRINT_ID)
    team_velocity(PROJECT_ID, SPRINT_ID)
    unplanned_work(PROJECT_ID, SPRINT_ID)
    focus_structure(PROJECT_ID, SPRINT_ID)
    defect_dynamics(PROJECT_ID)
