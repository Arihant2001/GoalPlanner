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
    assert len(tasks) >= 9, f"Expected at least 9 default tasks, got {len(tasks)}"
    print(f"PASS: /api/tasks returned {len(tasks)} tasks")

    # 3. Test matrix endpoint
    res = client.get('/api/matrix?year=2026&month=10')
    assert res.status_code == 200
    matrix = res.get_json()['data']
    assert len(matrix['days']) == 31, f"Expected 31 days in October, got {len(matrix['days'])}"
    assert len(matrix['matrix']) == len(tasks), f"Expected {len(tasks)} rows, got {len(matrix['matrix'])}"
    print(f"PASS: /api/matrix returned 31 days and {len(matrix['matrix'])} task rows")

    # 4. Test toggle endpoint
    sample_task_id = tasks[0]['id']
    test_date = '2026-10-26'
    res = client.post('/api/toggle', json={'task_id': sample_task_id, 'date': test_date, 'state': True})
    assert res.status_code == 200
    assert res.get_json()['result']['completed'] is True
    print(f"PASS: /api/toggle marked task {sample_task_id} completed on {test_date}")

    # Verify toggle in matrix
    res = client.get('/api/matrix?year=2026&month=10')
    matrix = res.get_json()['data']
    oct26_cell = matrix['matrix'][0]['cells'][25] # Day 26 (index 25)
    assert oct26_cell is True, "Cell was not marked true in matrix"
    print("PASS: Cell verified completed in matrix data")

    # 5. Test heatmap endpoint
    res = client.get('/api/heatmap?year=2026')
    assert res.status_code == 200
    heatmap = res.get_json()['data']
    assert len(heatmap['days']) == 365, f"Expected 365 days, got {len(heatmap['days'])}"
    assert heatmap['total_completed_actions'] >= 1
    print(f"PASS: /api/heatmap returned 365 days with active actions")

    # 6. Test yearly stats
    res = client.get('/api/yearly-stats?year=2026')
    assert res.status_code == 200
    stats = res.get_json()['data']
    assert len(stats['months']) == 12
    print(f"PASS: /api/yearly-stats returned 12 months")

    # 7. Test task creation
    res = client.post('/api/tasks', json={'title': 'Reading', 'category': 'Habit', 'color': '#8b5cf6'})
    assert res.status_code == 201
    new_task = res.get_json()['task']
    new_id = new_task['id']
    print(f"PASS: Created new task id={new_id} ('Reading')")

    # 8. Test export JSON & CSV
    res = client.get('/api/export?format=json')
    assert res.status_code == 200
    export_json = res.get_json()
    assert 'tasks' in export_json and 'completions' in export_json
    print("PASS: /api/export (JSON)")

    res = client.get('/api/export?format=csv')
    assert res.status_code == 200
    assert res.mimetype == 'text/csv'
    print("PASS: /api/export (CSV)")

    # Clean up test task
    client.delete(f'/api/tasks/{new_id}?hard=true')
    print("PASS: Cleaned up test task")

    print("\n=========================================")
    print(" ALL 8 INTEGRATION TESTS PASSED 100%! ")
    print("=========================================\n")

if __name__ == '__main__':
    run_tests()
