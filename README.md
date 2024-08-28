# Metrics

## 1. Sprint metrics
### About
This script collects:
* Sprint goals completion
* Development time:
  * Lead time
  * Cycle time
  * In review time
* Team velocity:
  * committed / completed
* Unplanned work
* Focus structure:
  * unplanned / bugs / roadmap / tech debt 
* Defect dynamics (medium+ bugs closed / open)

### How to collect
1. Generate your [API token in Atlassian](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create `auth.py` file with the following content:
```python
BASE_URL = "https://intento.atlassian.net" 
EMAIL = "XXX"  # Atlassian (Jira) user email 
TOKEN = "XXX"  # Atlassian (Jira) user API token
```
3. Create virtual env and install requirements:
```
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```
4. Make sure that the sprint is CLOSED
5. Run from command line with parameters, e.g.: 
```
python3 sprint_metrics.py --sprint XXX --project XXX > sprint_stat.txt
```
* `--project` - write project key
* `--sprint` - pass the sprint ID
* specify the result filename after `>` (or stats will be printed in STDOUT)
