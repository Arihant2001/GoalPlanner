from app import app
import json

def run_tests():
    client = app.test_client()
    
    # 1. Test index page
    res = client.get('/')
    assert res.status_code == 200, f"Index failed: {res.status_code}"
    print("PASS: Index page (200 OK)")

    # 2. Test tasks listing (Goal is row 0, Full Day is row 1)
    res = client.get('/api/tasks')
    assert res.status_code == 200
    tasks = res.get_json()['tasks']
    goal_task = next((t for t in tasks if t['title'].lower() == 'goal'), None)
    full_day_task = next((t for t in tasks if t['title'].lower() == 'full day'), None)
    assert goal_task is not None, "Goal task must exist"
    assert full_day_task is not None, "Full Day task must exist"
    print(f"PASS: /api/tasks returned {len(tasks)} tasks (Goal ID: {goal_task['id']}, Full Day ID: {full_day_task['id']})")

    # 3. Test matrix endpoint
    res = client.get('/api/matrix?year=2026&month=10')
    assert res.status_code == 200
    matrix = res.get_json()['data']
    assert len(matrix['days']) == 31, f"Expected 31 days in October, got {len(matrix['days'])}"
    assert matrix['matrix'][0]['task']['title'].lower() == 'goal', "First row in matrix must be Goal"
    assert matrix['matrix'][1]['task']['title'].lower() == 'full day', "Second row in matrix must be Full Day"
    print("PASS: /api/matrix returned Goal at row 0 and Full Day at row 1")

    # 4. Test Full Day single-task goal unlock
    res = client.post('/api/settings/threshold', json={'threshold': 3})
    assert res.status_code == 200

    regular_tasks = [t for t in tasks if t['title'].lower() not in ('goal', 'full day')]
    task_a = regular_tasks[0]['id']
    test_date = '2026-10-25'

    # Clear test date
    for t in tasks:
        client.post('/api/toggle', json={'task_id': t['id'], 'date': test_date, 'state': False})

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

    # 5. Test Streak continuity counts GOAL achievements
    # Let's set up 3 consecutive goal achievements: 2026-10-23, 2026-10-24, 2026-10-25
    d1, d2, d3 = '2026-10-23', '2026-10-24', '2026-10-25'
    task_b = regular_tasks[1]['id']
    task_c = regular_tasks[2]['id']

    # For d1: check 3 tasks (normal threshold)
    client.post('/api/toggle', json={'task_id': task_a, 'date': d1, 'state': True})
    client.post('/api/toggle', json={'task_id': task_b, 'date': d1, 'state': True})
    client.post('/api/toggle', json={'task_id': task_c, 'date': d1, 'state': True})

    # For d2: check 3 tasks
    client.post('/api/toggle', json={'task_id': task_a, 'date': d2, 'state': True})
    client.post('/api/toggle', json={'task_id': task_b, 'date': d2, 'state': True})
    client.post('/api/toggle', json={'task_id': task_c, 'date': d2, 'state': True})

    # For d3: check 1 task + Full Day
    client.post('/api/toggle', json={'task_id': task_a, 'date': d3, 'state': True})
    client.post('/api/toggle', json={'task_id': full_day_task['id'], 'date': d3, 'state': True})

    res = client.get('/api/heatmap?year=2026')
    assert res.status_code == 200
    heatmap = res.get_json()['data']
    assert heatmap['longest_streak'] >= 3, f"Expected longest streak >= 3 from Goal completions, got {heatmap['longest_streak']}"
    print(f"PASS: Longest streak ({heatmap['longest_streak']} days) accurately tracks Goal achievement continuity!")

    # 6. Test categories API
    res = client.get('/api/categories')
    assert res.status_code == 200
    assert len(res.get_json()['categories']) >= 6
    print("PASS: Categories API functional")

    # Reset test date
    for d in (d1, d2, d3):
        for t in tasks:
            client.post('/api/toggle', json={'task_id': t['id'], 'date': d, 'state': False})

    # 7. Test reorder tasks
    reg_tasks = [t for t in tasks if t['title'].lower() not in ('goal', 'full day')]
    if len(reg_tasks) >= 2:
        reversed_ids = [t['id'] for t in reversed(reg_tasks)]
        res = client.post('/api/tasks/reorder', json={'task_ids': reversed_ids})
        assert res.status_code == 200 and res.get_json()['success'] is True
        m_res = client.get('/api/matrix?year=2026&month=11').get_json()['data']
        assert m_res['matrix'][0]['task']['title'].lower() == 'goal'
        assert m_res['matrix'][1]['task']['title'].lower() == 'full day'
        assert m_res['matrix'][2]['task']['id'] == reversed_ids[0]
        print("PASS: /api/tasks/reorder keeps Goal/Full Day fixed and shifts regular tasks")

    # 8. Test level-1 nesting of tasks and automatic parent ticking
    # Create parent task 'Office'
    res = client.post('/api/tasks', json={'title': 'Office', 'category': 'Power'})
    assert res.status_code == 201
    office_task = res.get_json()['task']
    office_id = office_task['id']

    # Create subtask 'POC' under 'Office'
    res = client.post('/api/tasks', json={'title': 'POC', 'parent_id': office_id})
    assert res.status_code == 201
    poc_task = res.get_json()['task']
    assert poc_task['parent_id'] == office_id
    assert poc_task['category'] == ''  # No category
    print("PASS: Created level-1 subtask 'POC' under 'Office' with no category")

    # Creating subtask inside 'POC' must fail (level-1 max depth constraint)
    res = client.post('/api/tasks', json={'title': 'NestedInsidePOC', 'parent_id': poc_task['id']})
    assert res.status_code == 400
    print("PASS: Level-1 max depth enforced: creating subtask inside 'POC' is blocked")

    # Creating subtask under 'Goal' or 'Full Day' must fail
    res = client.post('/api/tasks', json={'title': 'SubGoal', 'parent_id': goal_task['id']})
    assert res.status_code == 400
    print("PASS: Creating subtask under system tasks (Goal/Full Day) is blocked")

    # Test automatic ticking: ticking 'POC' should automatically tick 'Office'
    test_nest_date = '2026-11-20'
    res = client.post('/api/toggle', json={'task_id': poc_task['id'], 'date': test_nest_date, 'state': True})
    assert res.status_code == 200

    # Verify 'Office' is now marked completed for test_nest_date
    m_res = client.get('/api/matrix?year=2026&month=11').get_json()['data']
    office_row = next(r for r in m_res['matrix'] if r['task']['id'] == office_id)
    poc_row = next(r for r in m_res['matrix'] if r['task']['id'] == poc_task['id'])
    
    # 20th of November is index 19
    assert poc_row['cells'][19] is True, "POC subtask should be checked"
    assert office_row['cells'][19] is True, "Office parent task should be automatically checked when POC is ticked"
    print("PASS: Ticking subtask 'POC' automatically ticked parent task 'Office'!")

    # Verify subtask 'POC' appears directly under 'Office' in matrix
    office_idx = next(i for i, r in enumerate(m_res['matrix']) if r['task']['id'] == office_id)
    poc_idx = next(i for i, r in enumerate(m_res['matrix']) if r['task']['id'] == poc_task['id'])
    assert poc_idx == office_idx + 1, "Subtask POC must appear directly beneath its parent Office"
    print("PASS: Subtask POC is rendered directly below parent Office")

    # Clean up test tasks
    client.delete(f'/api/tasks/{poc_task["id"]}?hard=true')
    client.delete(f'/api/tasks/{office_id}?hard=true')

    print("\n=========================================")
    print(" ALL 8 SPEC & REGRESSION TESTS PASSED 100%! ")
    print("=========================================\n")

if __name__ == '__main__':
    run_tests()
