from app import app
import json

def run_tests():
    client = app.test_client()
    
    # 1. Test index page (publicly accessible)
    res = client.get('/')
    assert res.status_code == 200, f"Index failed: {res.status_code}"
    print("PASS: Index page (200 OK)")

    # 2. Test unauthenticated API access blocked (401)
    res = client.get('/api/tasks')
    assert res.status_code == 401
    assert res.get_json()['requires_login'] is True
    print("PASS: Unauthenticated API access properly blocked with 401")

    # 3. Test Registration and Login for User 1
    u1_username = "arihant_test"
    u1_password = "password123"
    
    # Register or login if exists
    res = client.post('/api/auth/register', json={'username': u1_username, 'password': u1_password})
    if res.status_code == 400 and 'already taken' in res.get_json().get('error', ''):
        res = client.post('/api/auth/login', json={'username': u1_username, 'password': u1_password})
    assert res.status_code in (200, 201), f"Auth failed: {res.get_json()}"
    u1_data = res.get_json()['user']
    print(f"PASS: User 1 authenticated successfully as '{u1_data['username']}' (ID: {u1_data['id']})")

    # 4. Test tasks listing for User 1 (Goal is row 0, Full Day is row 1)
    res = client.get('/api/tasks')
    assert res.status_code == 200
    tasks = res.get_json()['tasks']
    goal_task = next((t for t in tasks if t['title'].lower() == 'goal'), None)
    full_day_task = next((t for t in tasks if t['title'].lower() == 'full day'), None)
    assert goal_task is not None, "Goal task must exist"
    assert full_day_task is not None, "Full Day task must exist"
    print(f"PASS: /api/tasks returned {len(tasks)} tasks (Goal ID: {goal_task['id']}, Full Day ID: {full_day_task['id']})")

    # 5. Test matrix endpoint
    res = client.get('/api/matrix?year=2026&month=10')
    assert res.status_code == 200
    matrix = res.get_json()['data']
    assert len(matrix['days']) == 31, f"Expected 31 days in October, got {len(matrix['days'])}"
    assert matrix['matrix'][0]['task']['title'].lower() == 'goal', "First row in matrix must be Goal"
    assert matrix['matrix'][1]['task']['title'].lower() == 'full day', "Second row in matrix must be Full Day"
    print("PASS: /api/matrix returned Goal at row 0 and Full Day at row 1")

    # 6. Test Full Day single-task goal unlock
    res = client.post('/api/settings/threshold', json={'threshold': 3})
    assert res.status_code == 200

    regular_tasks = [t for t in tasks if t['title'].lower() not in ('goal', 'full day')]
    if not regular_tasks:
        res = client.post('/api/tasks', json={'title': 'Testing Habit', 'category': 'Mind'})
        regular_tasks = [res.get_json()['task']]
        tasks.append(regular_tasks[0])
        
    task_a = regular_tasks[0]['id']
    test_date = '2026-10-25'

    # Clear test date
    for t in tasks:
        client.post('/api/toggle', json={'task_id': t['id'], 'date': test_date, 'state': False})

    # Test toggling Full Day when 0 tasks are checked: MUST FAIL WITH 400!
    res = client.post('/api/toggle', json={'task_id': full_day_task['id'], 'date': test_date, 'state': True})
    assert res.status_code == 400, f"Expected 400 when toggling Full Day with 0 tasks, got {res.status_code}"
    assert 'At least 1 habit must be checked' in res.get_json()['error']
    print("PASS: Toggling Full Day with 0 regular habits checked is blocked (400 Bad Request)")

    # Check 1 regular task only: Goal should be False (threshold is 3)
    client.post('/api/toggle', json={'task_id': task_a, 'date': test_date, 'state': True})
    res = client.get('/api/matrix?year=2026&month=10')
    goal_cells = res.get_json()['data']['matrix'][0]['cells']
    oct25_idx = 24
    assert goal_cells[oct25_idx] is False, "Goal should not be ticked with only 1 task without Full Day"
    print("PASS: 1 task alone does not tick Goal")

    # Now check 'Full Day': Goal should automatically turn True!
    client.post('/api/toggle', json={'task_id': full_day_task['id'], 'date': test_date, 'state': True})
    res = client.get('/api/matrix?year=2026&month=10')
    goal_cells = res.get_json()['data']['matrix'][0]['cells']
    assert goal_cells[oct25_idx] is True, "Goal MUST be ticked when Full Day is checked with 1 task!"
    print("PASS: Full Day + 1 task successfully achieved Goal!")

    # Uncheck the regular task: Goal should uncheck because 0 regular tasks are done
    client.post('/api/toggle', json={'task_id': task_a, 'date': test_date, 'state': False})
    res = client.get('/api/matrix?year=2026&month=10')
    goal_cells = res.get_json()['data']['matrix'][0]['cells']
    assert goal_cells[oct25_idx] is False, "Goal must not be ticked if 0 tasks were done even with Full Day checked"
    print("PASS: Full Day without any task does not tick Goal")

    # 7. Test categories API
    res = client.get('/api/categories')
    assert res.status_code == 200
    assert len(res.get_json()['categories']) >= 6
    print("PASS: Categories API functional")

    # 8. Test level-1 nesting of tasks and automatic parent ticking
    res = client.post('/api/tasks', json={'title': 'Office Work', 'category': 'Power'})
    assert res.status_code == 201
    office_task = res.get_json()['task']
    office_id = office_task['id']

    # Create subtask 'POC' under 'Office Work'
    res = client.post('/api/tasks', json={'title': 'POC Subtask', 'parent_id': office_id})
    assert res.status_code == 201
    poc_task = res.get_json()['task']
    assert poc_task['parent_id'] == office_id
    assert poc_task['category'] == ''
    print("PASS: Created level-1 subtask 'POC' under 'Office Work' with no category")

    # Level-1 max depth enforcement: creating subtask inside 'POC' must fail
    res = client.post('/api/tasks', json={'title': 'NestedSubtask', 'parent_id': poc_task['id']})
    assert res.status_code == 400
    print("PASS: Level-1 max depth enforced: creating subtask inside subtask is blocked")

    # Ticking subtask automatically ticks parent task
    test_nest_date = '2026-11-20'
    res = client.post('/api/toggle', json={'task_id': poc_task['id'], 'date': test_nest_date, 'state': True})
    assert res.status_code == 200

    m_res = client.get('/api/matrix?year=2026&month=11').get_json()['data']
    office_row = next(r for r in m_res['matrix'] if r['task']['id'] == office_id)
    poc_row = next(r for r in m_res['matrix'] if r['task']['id'] == poc_task['id'])
    nov20_idx = 19
    assert poc_row['cells'][nov20_idx] is True, "POC subtask should be checked"
    assert office_row['cells'][nov20_idx] is True, "Office parent task must automatically tick when POC is checked"
    print("PASS: Ticking subtask automatically ticked parent task!")

    # 9. Test Multi-User Isolation: User 2 registering and seeing a completely fresh dashboard
    client2 = app.test_client()
    u2_username = "bob_test_user"
    u2_password = "password456"

    res = client2.post('/api/auth/register', json={'username': u2_username, 'password': u2_password})
    if res.status_code == 400 and 'already taken' in res.get_json().get('error', ''):
        res = client2.post('/api/auth/login', json={'username': u2_username, 'password': u2_password})
    assert res.status_code in (200, 201)
    u2_data = res.get_json()['user']
    print(f"PASS: User 2 registered/authenticated as '{u2_data['username']}' (ID: {u2_data['id']})")

    # User 2 should have Goal and Full Day, but ZERO of User 1's tasks!
    res = client2.get('/api/tasks')
    assert res.status_code == 200
    u2_tasks = res.get_json()['tasks']
    u2_titles = [t['title'].lower() for t in u2_tasks]
    assert 'goal' in u2_titles and 'full day' in u2_titles
    assert 'office work' not in u2_titles, "User 2 must NOT see User 1's tasks!"
    assert 'poc subtask' not in u2_titles, "User 2 must NOT see User 1's subtasks!"
    print("PASS: User 2 has isolated dashboard: cannot see User 1's tasks")

    # User 2 creates their own task
    res = client2.post('/api/tasks', json={'title': 'Bob Unique Habit', 'category': 'Soul'})
    assert res.status_code == 201
    u2_unique_task = res.get_json()['task']

    # User 1 must NOT see User 2's task
    res = client.get('/api/tasks')
    u1_titles = [t['title'].lower() for t in res.get_json()['tasks']]
    assert 'bob unique habit' not in u1_titles, "User 1 must NOT see User 2's tasks!"
    print("PASS: User 1 cannot see User 2's tasks (strict multi-tenant isolation verified!)")

    print("\n=========================================")
    print(" ALL 9 MULTI-USER & REGRESSION TESTS PASSED 100%! ")
    print("=========================================\n")

if __name__ == '__main__':
    run_tests()
