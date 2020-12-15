from installed_clients.WorkspaceClient import Workspace

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
