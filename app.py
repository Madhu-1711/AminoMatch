"""AminoMatch: local, session-isolated data-structures teaching application."""

from collections import OrderedDict
from copy import deepcopy
from csv import Error as CsvError
from functools import wraps
from io import StringIO
from pathlib import Path
import secrets
from threading import RLock

from flask import Flask, jsonify, render_template, request, send_file, session
from werkzeug.exceptions import HTTPException

from nutrition import (ANALYSIS_METRICS, analysis_catalog, analyze,
                       complement_graph, finite_number, load_foods)
from structures import (LinkedList, Queue, Stack, balanced_food_tree, bfs,
                        binary_search, compare_sums, expression_demo,
                        linear_search, merge_sort, MaxHeap)

ROOT = Path(__file__).resolve().parent


class Workspace:
    def __init__(self, foods, source="Illustrative starter dataset"):
        self.foods = LinkedList(foods)
        self.practice_list = LinkedList(food.name for food in self.foods)
        self.source = source
        self.meal = []
        self.history = Stack()
        self.pending = Queue()
        self.next_job = 1
        self.tree = balanced_food_tree(self.foods)
        self.ordered = sorted(self.foods, key=lambda food: food.name.casefold())
        self.graph = complement_graph(self.foods)
        self.catalog = analysis_catalog(self.foods)
        self.priority = MaxHeap()
        self.priority_metric = "protein_g"

    def snapshot(self):
        foods = []
        for food in self.foods:
            profile = analyze([{"food_id": food.id, "grams": 100}], self.foods)
            foods.append({**food.to_dict(), "profile": profile})
        return {"foods": foods, "source": self.source, "meal": self.meal,
                "analysis": analyze(self.meal, self.foods), "undo_count": len(self.history),
                "queue": [{"id": job["id"], "portions": len(job["meal"])} for job in self.pending]}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(32), MAX_CONTENT_LENGTH=1024 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict")
    if test_config:
        app.config.update(test_config)
    with (ROOT / "data" / "foods.csv").open(encoding="utf-8-sig", newline="") as stream:
        starter = load_foods(stream)
    workspaces, lock = OrderedDict(), RLock()

    def stateful(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            # Reject cross-origin browser mutations even when no CORS is enabled.
            if request.method == "POST" and request.headers.get("Origin"):
                if request.headers["Origin"].rstrip("/") != request.host_url.rstrip("/"):
                    return jsonify(error="Cross-origin changes are not allowed."), 403
            with lock:
                key = session.get("workspace_id")
                if key not in workspaces:
                    key = secrets.token_hex(16)
                    session["workspace_id"] = key
                    workspaces[key] = Workspace(starter)
                    if len(workspaces) > 64:
                        workspaces.popitem(last=False)
                workspaces.move_to_end(key)
                return function(workspaces[key], *args, **kwargs)
        return wrapped

    def payload():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Send a JSON object.")
        return data

    @app.errorhandler(ValueError)
    def invalid_input(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return error

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    @stateful
    def state(workspace):
        return jsonify(workspace.snapshot())

    @app.post("/api/meal")
    @stateful
    def meal(workspace):
        data = payload()
        action = data.get("action")
        if action == "undo":
            workspace.meal = workspace.history.pop()
            return jsonify(workspace.snapshot())
        updated = deepcopy(workspace.meal)
        if action == "add":
            food_id = data.get("food_id")
            if not workspace.foods.find(lambda food: food.id == food_id):
                raise ValueError("Choose a food from the current dataset.")
            grams = finite_number(data.get("grams"), "Serving in grams", 1, 2000)
            if len(updated) >= 30:
                raise ValueError("A meal can have at most 30 portions.")
            updated.append({"food_id": food_id, "grams": grams})
        elif action == "example":
            for food_id in ("lentils", "brown-rice"):
                if not workspace.foods.find(lambda food: food.id == food_id):
                    raise ValueError("The sample pairing requires the starter foods.")
            updated = [{"food_id": "lentils", "grams": 100},
                       {"food_id": "brown-rice", "grams": 100}]
        elif action == "remove":
            index = data.get("index")
            if type(index) is not int or not 0 <= index < len(updated):
                raise ValueError("That portion does not exist.")
            updated.pop(index)
        elif action == "clear":
            updated = []
        else:
            raise ValueError("Unknown meal action.")
        if updated != workspace.meal:
            if len(workspace.history) >= 200:
                raise ValueError("Undo history is full. Reset the dataset to start a new session.")
            workspace.history.push(deepcopy(workspace.meal))
            workspace.meal = updated
        return jsonify(workspace.snapshot())

    @app.post("/api/queue")
    @stateful
    def queue(workspace):
        action = payload().get("action")
        result = None
        if action == "enqueue":
            if not workspace.meal:
                raise ValueError("Add at least one food before queuing an analysis.")
            if len(workspace.pending) >= 20:
                raise ValueError("Process an existing job first (20-job limit).")
            workspace.pending.enqueue({"id": workspace.next_job, "meal": deepcopy(workspace.meal)})
            workspace.next_job += 1
        elif action == "process":
            job = workspace.pending.dequeue()
            result = {"id": job["id"], "analysis": analyze(job["meal"], workspace.foods)}
        else:
            raise ValueError("Choose enqueue or process.")
        return jsonify(state=workspace.snapshot(), processed=result)

    @app.post("/api/list")
    @stateful
    def linked_list(workspace):
        data = payload()
        action = data.get("action")
        values = workspace.practice_list
        value, found, visited = None, None, []
        if action in ("append", "insert", "search"):
            value = data.get("value")
            if not isinstance(value, str) or not value.strip() or len(value) > 80:
                raise ValueError("Enter a node value of 1 to 80 characters.")
            value = value.strip()
        if action in ("append", "insert"):
            if len(values) >= 250:
                raise ValueError("The practice list has a 250-node limit.")
            if action == "append":
                values.append(value)
            else:
                values.insert(data.get("index"), value)
        elif action == "remove":
            value = values.remove(data.get("index"))
        elif action == "search":
            for index, candidate in enumerate(values):
                visited.append(index)
                if candidate.casefold() == value.casefold():
                    found = index
                    break
        elif action == "clear":
            workspace.practice_list = LinkedList()
        elif action == "reset":
            workspace.practice_list = LinkedList(food.name for food in workspace.foods)
        else:
            raise ValueError("Choose append, insert, remove, search, clear or reset.")
        return jsonify(linked=list(workspace.practice_list), value=value,
                       found=found, visited=visited)

    @app.post("/api/expression")
    @stateful
    def expression(workspace):
        return jsonify(expression_demo(payload().get("expression")))

    @app.get("/api/structures")
    @stateful
    def structures(workspace):
        order = request.args.get("order", "inorder")
        start = request.args.get("start", workspace.foods.head.value.id)
        target = request.args.get("target", "")
        return jsonify(
            linked=[food.name for food in workspace.foods],
            practice_linked=list(workspace.practice_list),
            efficiency=compare_sums([food.protein_g for food in workspace.foods]),
            tree=workspace.tree.hierarchy(), traversal=workspace.tree.traverse(order),
            search=binary_search(workspace.ordered, target) if target else None,
            graph=workspace.graph, bfs=bfs(workspace.graph, start, trace=True),
            history=list(workspace.history),
        )

    def heap_state(workspace):
        return {"items": workspace.priority.snapshot(), "metric": workspace.priority_metric}

    @app.get("/api/phase3")
    @stateful
    def phase3(workspace):
        metric = request.args.get("metric", "protein_g")
        direction = request.args.get("direction", "descending")
        category = request.args.get("category", "")
        target = request.args.get("target", "").strip()
        if metric not in ANALYSIS_METRICS:
            raise ValueError("Choose a supported analysis metric.")
        if direction not in ("ascending", "descending"):
            raise ValueError("Choose ascending or descending order.")
        if category and category not in {food.category for food in workspace.foods}:
            raise ValueError("Choose a category from the current dataset.")
        if len(target) > 80:
            raise ValueError("Search names must be at most 80 characters.")
        selected = [row for row in workspace.catalog if not category or row["category"] == category]
        sorted_result = merge_sort(selected, key=lambda row: row[metric], reverse=direction == "descending")
        rows = sorted_result["items"]
        food_by_id = {food.id: food for food in workspace.foods}
        ranked_foods = [food_by_id[row["id"]] for row in rows]
        name_order = merge_sort(ranked_foods, key=lambda food: food.name.casefold())["items"]
        binary = binary_search(name_order, target) if target else None
        if binary is not None:
            binary["items"] = [food.id for food in name_order]
        steps = [{**frame, "items": [row["id"] for row in frame["items"]]} for frame in sorted_result["steps"]]
        values = [row[metric] for row in rows]
        return jsonify(catalog=workspace.catalog, rows=rows, metric=metric, metrics=ANALYSIS_METRICS,
                       initial=[row["id"] for row in selected], target=target,
                       sort={"steps": steps, "comparisons": sorted_result["comparisons"]},
                       search=linear_search(ranked_foods, target) if target else None,
                       binary=binary, heap=heap_state(workspace),
                       summary={"count": len(values), "mean": sum(values) / len(values) if values else 0,
                                "minimum": min(values, default=0), "maximum": max(values, default=0)})

    @app.post("/api/priority")
    @stateful
    def priority(workspace):
        data = payload()
        action = data.get("action")
        removed, analysis, steps = None, None, []
        if action == "push":
            metric = data.get("metric", workspace.priority_metric)
            if not isinstance(metric, str) or metric not in ANALYSIS_METRICS:
                raise ValueError("Choose a supported priority metric.")
            if len(workspace.priority) and metric != workspace.priority_metric:
                raise ValueError("Clear or process the queue before changing its priority metric.")
            if len(workspace.priority) >= 20:
                raise ValueError("Process an entry first (20-entry limit).")
            row = next((row for row in workspace.catalog if row["id"] == data.get("food_id")), None)
            if row is None:
                raise ValueError("Choose a food from the current dataset.")
            steps = workspace.priority.push(row["id"], row[metric])
            workspace.priority_metric = metric
        elif action == "pop":
            entry = workspace.priority.peek()
            analysis = analyze([{"food_id": entry["value"], "grams": 100}], workspace.foods)
            result = workspace.priority.pop()
            removed, steps = result["removed"], result["steps"]
        elif action == "clear":
            workspace.priority = MaxHeap()
            steps = [{"action": "Queue cleared", "items": []}]
        else:
            raise ValueError("Choose push, pop or clear.")
        return jsonify(heap=heap_state(workspace), removed=removed, analysis=analysis, steps=steps)

    @app.get("/api/dataset/template")
    def template():
        return send_file(ROOT / "data" / "foods.csv", as_attachment=True,
                         download_name="aminomatch-template.csv")

    @app.post("/api/dataset")
    @stateful
    def dataset(workspace):
        if request.is_json:
            if payload().get("action") != "reset":
                raise ValueError("Choose reset or upload a CSV file.")
            foods, source = starter, "Illustrative starter dataset"
        else:
            upload = request.files.get("file")
            if not upload or not upload.filename.lower().endswith(".csv"):
                raise ValueError("Choose a UTF-8 CSV file.")
            try:
                text = upload.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                raise ValueError("Save the CSV using UTF-8 encoding.") from None
            try:
                foods = load_foods(StringIO(text, newline=""))
            except CsvError as error:
                raise ValueError("The CSV could not be read.") from error
            source = "User-imported dataset · values not independently verified"
        replacement = Workspace(foods, source)
        workspaces[session["workspace_id"]] = replacement
        return jsonify(replacement.snapshot())

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)