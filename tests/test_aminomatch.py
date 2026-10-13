import csv
from io import BytesIO, StringIO
import json
from pathlib import Path
import unittest

from app import create_app
from nutrition import AMINO_ACIDS, CSV_FIELDS, analyze, complement_graph, load_foods
from structures import (BinarySearchTree, LinkedList, Queue, Stack,
                        balanced_food_tree, bfs, binary_search, compare_sums,
                        expression_demo, linear_search, merge_sort, MaxHeap)

ROOT = Path(__file__).resolve().parents[1]


def starter_foods():
    with (ROOT / "data" / "foods.csv").open(encoding="utf-8", newline="") as stream:
        return load_foods(stream)


def dataset_csv(rows):
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class StructureTests(unittest.TestCase):
    def test_linear_search_first_last_missing_and_empty(self):
        foods = starter_foods()
        for index in (0, len(foods) - 1):
            result = linear_search(foods, foods[index].name.upper())
            self.assertEqual(result["index"], index)
            self.assertEqual(len(result["steps"]), index + 1)
        self.assertIsNone(linear_search(foods, "missing")["found"])
        self.assertEqual(linear_search([], "missing")["steps"], [])

    def test_merge_sort_stability_and_trace(self):
        values = [(2, "first"), (1, "low"), (2, "second"), (3, "high")]
        for reverse in (False, True):
            result = merge_sort(values, key=lambda value: value[0], reverse=reverse)
            self.assertEqual(result["items"], sorted(values, key=lambda value: value[0], reverse=reverse))
            self.assertEqual(result["steps"][-1]["items"], result["items"])
            self.assertEqual(len(result["steps"]), len(values) - 1)
        self.assertEqual(values[0], (2, "first"))
        self.assertEqual(merge_sort([])["items"], [])
        self.assertEqual(merge_sort([1])["steps"], [])

    def test_heap_priority_ties_invariants_and_trace(self):
        heap = MaxHeap()
        priorities = [3, 8, 2, 8, 1, 9, 4, 6, 9]
        for index, priority in enumerate(priorities):
            frames = heap.push(index, priority)
            self.assertEqual(frames[-1]["items"], heap.snapshot())
            for child in range(1, len(heap)):
                self.assertFalse(heap.higher(heap.items[child], heap.items[(child - 1) // 2]))
        original_frame = frames[-1]["items"]
        expected = sorted(range(len(priorities)), key=lambda index: -priorities[index])
        self.assertEqual(heap.peek()["value"], expected[0])
        self.assertEqual([heap.pop()["removed"]["value"] for index in priorities], expected)
        self.assertEqual(len(original_frame), len(priorities))
        with self.assertRaises(ValueError):
            heap.pop()
        with self.assertRaises(ValueError):
            heap.peek()
        for priority in (True, float("nan"), float("inf"), "5"):
            with self.assertRaises(ValueError):
                heap.push("bad", priority)
        self.assertEqual(len(heap), 0)
        heap.push("again", 1)
        self.assertEqual(heap.pop()["removed"]["value"], "again")

    def test_linked_list_append_and_find(self):
        values = LinkedList()
        self.assertEqual(list(values), [])
        for value in (3, 1, 4):
            values.append(value)
        self.assertEqual(list(values), [3, 1, 4])
        self.assertEqual(len(values), 3)
        self.assertEqual(values.head.value, 3)
        self.assertEqual(values.tail.value, 4)
        self.assertIsNone(values.tail.next)
        self.assertEqual(values.find(lambda x: x == 1), 1)
        self.assertIsNone(values.find(lambda x: x == 9))

    def test_linked_list_insert_remove_and_reuse(self):
        values = LinkedList()
        values.insert(0, "middle")
        values.insert(0, "head")
        values.insert(2, "tail")
        values.insert(1, "inner")
        self.assertEqual(list(values), ["head", "inner", "middle", "tail"])
        self.assertEqual(values.remove(1), "inner")
        self.assertEqual(values.remove(2), "tail")
        self.assertEqual(values.tail.value, "middle")
        self.assertIsNone(values.tail.next)
        self.assertEqual(values.remove(0), "head")
        self.assertEqual(values.remove(0), "middle")
        self.assertIsNone(values.head)
        self.assertIsNone(values.tail)
        self.assertEqual(len(values), 0)
        values.append("again")
        self.assertIs(values.head, values.tail)
        for index in (-1, 2, True, "0", None):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    values.insert(index, "invalid")
                with self.assertRaises(ValueError):
                    values.remove(index)
                self.assertEqual(list(values), ["again"])

    def test_stack_lifo_and_underflow(self):
        stack = Stack()
        for value in (1, 2, 3):
            stack.push(value)
        self.assertEqual(stack.peek(), 3)
        self.assertEqual([stack.pop(), stack.pop(), stack.pop()], [3, 2, 1])
        self.assertEqual(len(stack), 0)
        with self.assertRaises(ValueError):
            stack.pop()
        with self.assertRaises(ValueError):
            stack.peek()

    def test_queue_fifo_tail_reset_and_reuse(self):
        queue = Queue()
        queue.enqueue(1)
        queue.enqueue(2)
        self.assertEqual(list(queue), [1, 2])
        self.assertEqual([queue.dequeue(), queue.dequeue()], [1, 2])
        self.assertIsNone(queue.items.tail)
        with self.assertRaises(ValueError):
            queue.dequeue()
        queue.enqueue(3)
        self.assertEqual(queue.dequeue(), 3)

    def test_expression_precedence_and_associativity(self):
        cases = [("(9 + 2.6) * 2", "9 2.6 + 2 *", 23.2),
                 ("8 / 4 / 2", "8 4 / 2 /", 1),
                 ("1 + 2 * 3", "1 2 3 * +", 7),
                 (".5 + (2 - 4)", ".5 2 4 - +", -1.5)]
        for expression, postfix, expected in cases:
            with self.subTest(expression=expression):
                result = expression_demo(expression)
                self.assertEqual(result["postfix"], postfix)
                self.assertAlmostEqual(result["result"], expected)

    def test_expression_invalid_input(self):
        cases = ["", "1 +", "(1+2", "1+2)", "()", "1 2", "2(3)", "1..2",
                 "-1", "2 ** 3", "__import__('os')", "1/0", "(1)(2)", None, "1" * 201]
        for expression in cases:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                expression_demo(expression)

    def test_expression_length_limit(self):
        with self.assertRaises(ValueError):
            expression_demo("1 + " * 50 + "1")

    def test_iterative_recursive_equivalence(self):
        for values in ([], [1], [1, 2.5, 3], list(range(250))):
            result = compare_sums(values)
            self.assertEqual(result["iterative_sum"], result["recursive_sum"])
            self.assertEqual(result["additions"], len(values))
            self.assertEqual(result["recursive_calls"], len(values) + 1)

    def test_binary_tree_traversals(self):
        foods = sorted(starter_foods()[:3], key=lambda food: food.name.casefold())
        tree = BinarySearchTree()
        for i in (1, 0, 2):
            tree.insert(foods[i])
        for order, indices in (("inorder", [0, 1, 2]), ("preorder", [1, 0, 2]), ("postorder", [0, 2, 1])):
            self.assertEqual(tree.traverse(order), [foods[i].name for i in indices])
        with self.assertRaises(ValueError):
            tree.traverse("invalid")

    def test_balanced_tree_contains_all_foods(self):
        foods = starter_foods()
        tree = balanced_food_tree(foods)
        self.assertEqual(tree.traverse(), sorted([food.name for food in foods], key=str.casefold))
        self.assertIsNotNone(tree.hierarchy()["left"])
        self.assertEqual(balanced_food_tree([]).traverse(), [])

    def test_binary_search_boundaries_and_missing(self):
        foods = sorted(starter_foods(), key=lambda food: food.name.casefold())
        for food in foods:
            result = binary_search(foods, food.name.upper())
            self.assertEqual(result["found"]["id"], food.id)
            self.assertLessEqual(len(result["steps"]), 4)
        self.assertIsNone(binary_search(foods, "missing")["found"])
        self.assertEqual(binary_search([], "anything")["steps"], [])

    def test_bfs_cycle_and_disconnected_component(self):
        graph = {"a": ["b", "c"], "b": ["a", "c"], "c": ["a", "b"], "d": []}
        self.assertEqual(bfs(graph, "a")["order"], ["a", "b", "c"])
        self.assertEqual(bfs(graph, "d")["order"], ["d"])
        self.assertEqual(len(bfs(graph, "a")["discovery_edges"]), 2)
        with self.assertRaises(ValueError):
            bfs(graph, "x")


class NutritionTests(unittest.TestCase):
    def setUp(self):
        self.foods = LinkedList(starter_foods())

    def test_starter_schema(self):
        self.assertEqual(len(self.foods), 12)
        self.assertEqual(set(self.foods.head.value.amino), set(AMINO_ACIDS))

    def test_empty_analysis(self):
        result = analyze([], self.foods)
        self.assertEqual(result["protein_g"], 0)
        self.assertEqual(result["score"], 0)
        self.assertIsNone(result["limiting"])
        self.assertFalse(result["meets_pattern"])

    def test_serving_scaling_and_score_invariance(self):
        full = analyze([{"food_id": "lentils", "grams": 100}], self.foods)
        half = analyze([{"food_id": "lentils", "grams": 50}], self.foods)
        self.assertEqual(half["protein_g"], 4.5)
        self.assertAlmostEqual(full["essential_mg"], half["essential_mg"] * 2)
        self.assertEqual(full["score"], half["score"])
        self.assertAlmostEqual(full["amino_mg"]["lysine"], 630)

    def test_combined_groups_and_essential_only_total(self):
        result = analyze([{"food_id": "lentils", "grams": 100}], self.foods)
        sulfur = next(group for group in result["groups"] if group["name"].startswith("Methionine"))
        self.assertEqual(sulfur["amount_mg"], 77 + 118)
        self.assertEqual(sulfur["target_mg"], 9 * 22)
        self.assertEqual(result["essential_mg"], sum(result["amino_mg"].values()) - 118 - 241)

    def test_example_pair_meets_pattern(self):
        result = analyze([{"food_id": "lentils", "grams": 100}, {"food_id": "brown-rice", "grams": 100}], self.foods)
        self.assertEqual(result["protein_g"], 11.6)
        self.assertTrue(result["meets_pattern"])
        self.assertEqual(result["met_count"], 9)

    def test_graph_is_symmetric_and_rule_holds(self):
        graph = complement_graph(self.foods)
        singles = {food.id: analyze([{"food_id": food.id, "grams": 100}], self.foods)["score"] for food in self.foods}
        for left, neighbors in graph.items():
            self.assertNotIn(left, neighbors)
            for right in neighbors:
                self.assertIn(left, graph[right])
                pair = analyze([{"food_id": left, "grams": 100}, {"food_id": right, "grams": 100}], self.foods)
                self.assertGreater(pair["score"], min(singles[left], singles[right]) + 4.99)

    def test_csv_round_trip(self):
        output = dataset_csv([food.to_dict() for food in self.foods])
        self.assertEqual(len(load_foods(StringIO(output))), 12)

    def test_csv_invalid_values(self):
        original = self.foods.head.value.to_dict()
        cases = [("protein_g", "nan"), ("protein_g", 0), ("protein_g", 101),
                 ("histidine_mg", ""), ("histidine_mg", -2), ("lysine_mg", "inf"),
                 ("leucine_mg", 100000), ("id", "Bad ID"), ("name", "")]
        for key, value in cases:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                load_foods(StringIO(dataset_csv([{**original, key: value}])))

    def test_csv_duplicates_headers_and_empty(self):
        row = self.foods.head.value.to_dict()
        for content in (dataset_csv([row, row]), "id,name\nx,y\n", dataset_csv([])):
            with self.assertRaises(ValueError):
                load_foods(StringIO(content))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-only"})
        self.client = self.app.test_client()

    def post(self, route, data):
        response = self.client.post(route, json=data)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_home_and_assets(self):
        for path in ("/", "/static/app.js", "/static/styles.css", "/api/dataset/template"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            response.close()

    def test_meal_add_remove_clear_undo(self):
        state = self.post("/api/meal", {"action": "add", "food_id": "lentils", "grams": 150})
        self.assertEqual(state["analysis"]["protein_g"], 13.5)
        self.assertEqual(state["undo_count"], 1)
        self.assertEqual(self.post("/api/meal", {"action": "remove", "index": 0})["meal"], [])
        self.assertEqual(len(self.post("/api/meal", {"action": "undo"})["meal"]), 1)
        self.assertEqual(self.post("/api/meal", {"action": "clear"})["meal"], [])

    def test_visualizer_history_and_bfs_steps(self):
        self.post("/api/meal", {"action": "add", "food_id": "lentils", "grams": 100})
        self.post("/api/meal", {"action": "add", "food_id": "brown-rice", "grams": 50})
        data = self.client.get("/api/structures?start=lentils").get_json()
        self.assertEqual(data["history"], [[{"food_id": "lentils", "grams": 100}], []])
        steps = data["bfs"]["steps"]
        self.assertEqual(steps[0]["queue"], ["lentils"])
        self.assertEqual(steps[-1]["queue"], [])
        self.assertEqual([step["current"] for step in steps[1:]], data["bfs"]["order"])
        self.post("/api/meal", {"action": "undo"})
        self.assertEqual(self.client.get("/api/structures").get_json()["history"], [[]])

    def test_bfs_trace_cycle_and_isolated_node(self):
        graph = {"a": ["b", "c"], "b": ["a", "c"], "c": ["a", "b"], "d": []}
        result = bfs(graph, "a", trace=True)
        self.assertEqual([step["queue"] for step in result["steps"]],
                         [["a"], ["b", "c"], ["c"], []])
        self.assertEqual([step["discovered"] for step in result["steps"]],
                         [["a"], ["b", "c"], [], []])
        self.assertEqual(bfs(graph, "d", trace=True)["order"], ["d"])
        self.assertEqual(bfs(graph, "d", trace=True)["steps"][-1]["queue"], [])

    def test_invalid_meal_is_atomic(self):
        for data in ({"action": "add", "food_id": "lentils", "grams": -1},
                     {"action": "add", "food_id": "lentils", "grams": "nan"},
                     {"action": "add", "food_id": "lentils", "grams": True},
                     {"action": "add", "food_id": "missing", "grams": 100},
                     {"action": "remove", "index": -1}, {"action": "remove", "index": True},
                     {"action": "undo"}, {"action": "unknown"}):
            self.assertEqual(self.client.post("/api/meal", json=data).status_code, 400)
        result = self.client.get("/api/state").get_json()
        self.assertEqual(result["meal"], [])
        self.assertEqual(result["undo_count"], 0)

    def test_queue_fifo_snapshot_independence(self):
        self.post("/api/meal", {"action": "add", "food_id": "lentils", "grams": 100})
        self.post("/api/queue", {"action": "enqueue"})
        self.post("/api/meal", {"action": "add", "food_id": "brown-rice", "grams": 100})
        self.post("/api/queue", {"action": "enqueue"})
        first = self.post("/api/queue", {"action": "process"})
        self.assertEqual(first["processed"]["id"], 1)
        self.assertEqual(first["processed"]["analysis"]["protein_g"], 9)
        second = self.post("/api/queue", {"action": "process"})
        self.assertEqual(second["processed"]["id"], 2)
        self.assertEqual(second["processed"]["analysis"]["protein_g"], 11.6)

    def test_practice_list_operations_and_isolation(self):
        original = self.client.get("/api/state").get_json()
        self.assertEqual(self.post("/api/list", {"action": "clear"})["linked"], [])
        self.post("/api/list", {"action": "append", "value": "Rice"})
        self.post("/api/list", {"action": "insert", "index": 0, "value": "Lentils"})
        result = self.post("/api/list", {"action": "append", "value": "Rice"})
        self.assertEqual(result["linked"], ["Lentils", "Rice", "Rice"])
        found = self.post("/api/list", {"action": "search", "value": "RICE"})
        self.assertEqual(found["found"], 1)
        self.assertEqual(found["visited"], [0, 1])
        missing = self.post("/api/list", {"action": "search", "value": "Missing"})
        self.assertIsNone(missing["found"])
        self.assertEqual(missing["visited"], [0, 1, 2])
        self.assertEqual(self.post("/api/list", {"action": "remove", "index": 2})["linked"], ["Lentils", "Rice"])
        structures = self.client.get("/api/structures").get_json()
        self.assertEqual(structures["practice_linked"], ["Lentils", "Rice"])
        self.assertEqual(structures["linked"], [food["name"] for food in original["foods"]])
        self.assertEqual(self.client.get("/api/state").get_json(), original)
        other = self.app.test_client().get("/api/structures").get_json()
        self.assertEqual(len(other["practice_linked"]), len(original["foods"]))
        reset = self.post("/api/list", {"action": "reset"})
        self.assertEqual(reset["linked"], [food["name"] for food in original["foods"]])

    def test_practice_list_invalid_operations_are_atomic(self):
        self.post("/api/list", {"action": "clear"})
        for data in ({"action": "append", "value": " "},
                     {"action": "append", "value": 2},
                     {"action": "append", "value": "x" * 81},
                     {"action": "insert", "value": "Rice", "index": True},
                     {"action": "insert", "value": "Rice", "index": 1},
                     {"action": "remove", "index": 0}, {"action": "bad"}):
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/api/list", json=data).status_code, 400)
                self.assertEqual(self.client.get("/api/structures").get_json()["practice_linked"], [])
        empty = self.post("/api/list", {"action": "search", "value": "Rice"})
        self.assertIsNone(empty["found"])
        self.assertEqual(empty["visited"], [])

    def test_queue_underflow_and_reuse(self):
        self.assertEqual(self.client.post("/api/queue", json={"action": "process"}).status_code, 400)
        self.assertEqual(self.client.post("/api/queue", json={"action": "enqueue"}).status_code, 400)
        self.post("/api/meal", {"action": "example"})
        for job_id in (1, 2):
            queued = self.post("/api/queue", {"action": "enqueue"})
            self.assertEqual(queued["state"]["queue"][0]["id"], job_id)
            processed = self.post("/api/queue", {"action": "process"})
            self.assertEqual(processed["processed"]["id"], job_id)
            self.assertEqual(processed["state"]["queue"], [])

    def test_phase3_sort_search_and_heatmap_values(self):
        result = self.client.get("/api/phase3?target=LENTILS%20(COOKED)").get_json()
        self.assertEqual([row["protein_g"] for row in result["rows"]], sorted([food.protein_g for food in starter_foods()], reverse=True))
        self.assertEqual(result["search"]["found"]["id"], "lentils")
        self.assertEqual(result["binary"]["found"]["id"], "lentils")
        names = {row["id"]: row["name"] for row in result["catalog"]}
        ordered_names = [names[food_id] for food_id in result["binary"]["items"]]
        self.assertEqual(ordered_names, sorted(ordered_names, key=str.casefold))
        self.assertEqual(result["sort"]["steps"][-1]["items"], [row["id"] for row in result["rows"]])
        for row in result["rows"]:
            profile = analyze([{"food_id": row["id"], "grams": 100}], LinkedList(starter_foods()))
            self.assertEqual(row["groups"], profile["groups"])
        filtered = self.client.get("/api/phase3?category=Grains&metric=score&direction=ascending&target=missing").get_json()
        self.assertTrue(all(row["category"] == "Grains" for row in filtered["rows"]))
        self.assertEqual([row["score"] for row in filtered["rows"]], sorted(row["score"] for row in filtered["rows"]))
        self.assertIsNone(filtered["search"]["found"])
        self.assertIsNone(filtered["binary"]["found"])
        for query in ("metric=bad", "direction=bad", "category=bad", "target=" + "x" * 81):
            self.assertEqual(self.client.get("/api/phase3?" + query).status_code, 400)

    def test_priority_processing_limits_isolation_and_reset(self):
        self.assertEqual(self.client.post("/api/priority", json={"action": "pop"}).status_code, 400)
        for food_id in ("brown-rice", "lentils", "lentils"):
            self.post("/api/priority", {"action": "push", "food_id": food_id, "metric": "protein_g"})
        previous = self.client.get("/api/phase3").get_json()["heap"]
        for payload in ({"action": "push", "food_id": "missing"},
                        {"action": "push", "food_id": "lentils", "metric": "score"},
                        {"action": "push", "food_id": "lentils", "metric": []}, {"action": "bad"}):
            self.assertEqual(self.client.post("/api/priority", json=payload).status_code, 400)
            self.assertEqual(self.client.get("/api/phase3").get_json()["heap"], previous)
        self.assertEqual(self.app.test_client().get("/api/phase3").get_json()["heap"]["items"], [])
        for order in (1, 2, 0):
            result = self.post("/api/priority", {"action": "pop"})
            self.assertEqual(result["removed"]["order"], order)
            self.assertEqual(result["analysis"]["protein_g"], result["removed"]["priority"])
        for index in range(20):
            self.post("/api/priority", {"action": "push", "food_id": "lentils", "metric": "score"})
        self.assertEqual(self.client.post("/api/priority", json={"action": "push", "food_id": "lentils", "metric": "score"}).status_code, 400)
        self.assertEqual(self.post("/api/priority", {"action": "clear"})["heap"]["items"], [])
        self.post("/api/priority", {"action": "push", "food_id": "lentils"})
        self.post("/api/dataset", {"action": "reset"})
        self.assertEqual(self.client.get("/api/phase3").get_json()["heap"]["items"], [])

    def test_session_isolation(self):
        self.post("/api/meal", {"action": "example"})
        other = self.app.test_client().get("/api/state").get_json()
        self.assertEqual(other["meal"], [])

    def test_import_and_reset(self):
        self.post("/api/meal", {"action": "example"})
        row = starter_foods()[0].to_dict()
        response = self.client.post("/api/dataset", data={"file": (BytesIO(dataset_csv([row]).encode()), "foods.csv")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["foods"]), 1)
        self.assertEqual(response.get_json()["meal"], [])
        self.assertEqual(response.get_json()["undo_count"], 0)
        reset = self.post("/api/dataset", {"action": "reset"})
        self.assertEqual(len(reset["foods"]), 12)

    def test_invalid_import_preserves_state(self):
        previous = self.post("/api/meal", {"action": "example"})
        response = self.client.post("/api/dataset", data={"file": (BytesIO(b"wrong,columns\n1,2"), "bad.csv")})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/state").get_json(), previous)

    def test_api_input_and_origin_errors(self):
        for body in ([], None, "text"):
            response = self.client.post("/api/meal", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/api/meal", json={"action": "clear"}, headers={"Origin": "https://other.example"}).status_code, 403)

    def test_structure_and_expression_endpoints(self):
        result = self.client.get("/api/structures?order=preorder&target=Lentils%20(cooked)&start=lentils")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()["search"]["found"]["id"], "lentils")
        self.assertEqual(result.get_json()["bfs"]["order"][0], "lentils")
        self.assertEqual(self.post("/api/expression", {"expression": "(9 + 2.6) * 2"})["result"], 23.2)
        self.assertEqual(self.client.get("/api/structures?order=bad").status_code, 400)
        self.assertEqual(self.client.get("/api/structures?start=bad").status_code, 400)


if __name__ == "__main__":
    unittest.main()