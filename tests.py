from app import app
import json

def run_tests():
    client = app.test_client()
    
    # 1. Test index page
    res = client.get('/')
    assert res.status_code == 200, f"Index failed: {res.status_code}"
    print("PASS: Index page (200 OK)")

    # 2. Test tasks listing
    res = client.get('/api/tasks')
    assert res.status_code == 200
    tasks = res.get_json()['tasks']
    goal_task = next((t for t in tasks if t['title'].lower() == 'goal'), None)
    assert goal_task is not None, "Goal task must exist"
    print(f"PASS: /api/tasks returned {len(tasks)} tasks (Goal ID: {goal_task['id']})")

    # 3. Test matrix endpoint
    res = client.get('/api/matrix?year=2026&month=10')
    assert res.status_code == 200
    matrix = res.get_json()['data']
    assert len(matrix['days']) == 31, f"Expected 31 days in October, got {len(matrix['days'])}"
    assert matrix['matrix'][0]['task']['title'].lower() == 'goal', "First row in matrix must be Goal"
    print(f"PASS: /api/matrix returned 31 days with Goal as first row")

    # 4. Test Goal cannot be manually toggled
    res = client.post('/api/toggle', json={'task_id': goal_task['id'], 'date': '2026-10-31', 'state': True})
    assert res.status_code == 400, "Manually toggling Goal must be rejected"
    print("PASS: Manually toggling Goal correctly rejected (400)")

    # 5. Test Goal auto-ticking based on threshold
    # Set threshold to 2 tasks
    res = client.post('/api/settings/threshold', json={'threshold': 2})
    assert res.status_code == 200
    assert res.get_json()['threshold'] == 2

    # Pick 2 non-goal tasks
    non_goal_tasks = [t for t in tasks if t['title'].lower() != 'goal']
    task_a = non_goal_tasks[0]['id']
    task_b = non_goal_tasks[1]['id']
    test_date = '2026-10-31'

    # Check 1 task: Goal should NOT be ticked yet
    client.post('/api/toggle', json={'task_id': task_a, 'date': test_date, 'state': True})
    res = client.get('/api/matrix?year=2026&month=10')
    goal_row = res.get_json()['data']['matrix'][0]
    oct31_idx = 30 # Day 31
    assert goal_row['cells'][oct31_idx] is False, "Goal should not be ticked with only 1 task"
    print("PASS: Goal remains unticked when completed count < threshold")

    # Check 2nd task: Goal SHOULD automatically become ticked!
    client.post('/api/toggle', json={'task_id': task_b, 'date': test_date, 'state': True})
    res = client.get('/api/matrix?year=2026&month=10')
    goal_row = res.get_json()['data']['matrix'][0]
    assert goal_row['cells'][oct31_idx] is True, "Goal must auto-tick when threshold (2) is reached"
    print("PASS: Goal automatically ticked when threshold (2 tasks) reached!")

    # Untick task_b: Goal should automatically become unticked
    client.post('/api/toggle', json={'task_id': task_b, 'date': test_date, 'state': False})
    res = client.get('/api/matrix?year=2026&month=10')
    goal_row = res.get_json()['data']['matrix'][0]
    assert goal_row['cells'][oct31_idx] is False, "Goal must auto-untick when dropping below threshold"
    print("PASS: Goal automatically unticked when dropping below threshold!")

    # 6. Test heatmap does NOT count Goal
    res = client.get('/api/heatmap?year=2026')
    assert res.status_code == 200
    heatmap = res.get_json()['data']
    oct31_heatmap_day = next((d for d in heatmap['days'] if d['date'] == test_date), None)
    assert 'Goal' not in oct31_heatmap_day['completed_tasks'], "Goal must not appear in heatmap completed tasks"
    print("PASS: Heatmap successfully excludes 'Goal'")

    # 7. Test task creation with Infinity Stone category & auto-color
    res = client.post('/api/tasks', json={'title': 'Time Management', 'category': 'Time'})
    assert res.status_code == 201
    new_task = res.get_json()['task']
    assert new_task['color'] == '#22c55e', f"Expected Time green #22c55e, got {new_task['color']}"
    print(f"PASS: Created task with Category 'Time' auto-assigned color {new_task['color']}")

    # 8. Test Goal cannot be deleted or archived
    res = client.delete(f"/api/tasks/{goal_task['id']}")
    assert res.status_code == 400, "Goal task deletion must be rejected"
    print("PASS: Goal deletion rejected (400)")

    # Clean up test task
    client.delete(f"/api/tasks/{new_task['id']}?hard=true")

    # Reset threshold back to 3
    client.post('/api/settings/threshold', json={'threshold': 3})

    print("\n=========================================")
    print(" ALL 8 V2.0 SPEC TESTS PASSED 100%! ")
    print("=========================================\n")

if __name__ == '__main__':
    run_tests()
