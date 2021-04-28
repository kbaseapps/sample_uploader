import os

from installed_clients.WorkspaceClient import Workspace
from jinja2 import Environment, PackageLoader, select_autoescape


env = Environment(
    loader=PackageLoader('sample_uploader','utils/templates'),
    autoescape=select_autoescape(['html'])
)

def get_workspace_user_perms(workspace_url, workspace_id, token, owner, acls):
    """
    """
    ws_client = Workspace(workspace_url, token=token)
    results = ws_client.get_permissions_mass({'workspaces': [{'id': workspace_id}]})
    for user in results['perms'][0]:
        # skip owner of the samples.
        if user == owner:
            continue
        if user == "*":
            # set public read to true (>0).
            acls['public_read'] = 1
            continue
        if results['perms'][0][user] == 'a':
            acls['admin'].append(user)
        if results['perms'][0][user] == 'r':
            acls['read'].append(user)
        if results['perms'][0][user] == 'w':
            acls['write'].append(user)
        if results['perms'][0][user] == 'n':
            continue
    return acls


def error_ui(errors, error_table_html, scratch):
    """
    TODO: make this better/change it all
    errors: list of errors
    scratch: kbase scratch space
    """
    template = env.get_template('index.html')
    html_path = os.path.join(scratch, 'index.html')
    rendered_html = template.render(
        results=errors,
        table=error_table_html
    )
    with open(html_path, 'w') as f:
        f.write(rendered_html)
    return html_path
