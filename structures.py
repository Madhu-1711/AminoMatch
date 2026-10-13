"""Small, explicit data-structure implementations for the two project phases."""

from dataclasses import dataclass
import math
import re
from typing import Any, Iterator


@dataclass
class Node:
    value: Any
    next: "Node | None" = None


class LinkedList:
    """Singly linked food storage; O(1) append, O(n) lookup."""

    def __init__(self, values=()):
        self.head = self.tail = None
        self.size = 0
        for value in values:
            self.append(value)

    def append(self, value):
        node = Node(value)
        if self.tail:
            self.tail.next = node
        else:
            self.head = node
        self.tail = node
        self.size += 1

    def insert(self, index, value):
        if type(index) is not int or not 0 <= index <= self.size:
            raise ValueError("Choose an insertion index between 0 and the list size.")
        if index == self.size:
            self.append(value)
            return
        if index == 0:
            self.head = Node(value, self.head)
        else:
            previous = self.head
            for position in range(index - 1):
                previous = previous.next
            previous.next = Node(value, previous.next)
        self.size += 1

    def remove(self, index):
        if type(index) is not int or not 0 <= index < self.size:
            raise ValueError("Choose an existing node index.")
        if index == 0:
            removed = self.head
            self.head = removed.next
            if self.size == 1:
                self.tail = None
        else:
            previous = self.head
            for position in range(index - 1):
                previous = previous.next
            removed = previous.next
            previous.next = removed.next
            if removed is self.tail:
                self.tail = previous
        self.size -= 1
        return removed.value

    def find(self, predicate):
        for value in self:
            if predicate(value):
                return value
        return None

    def __iter__(self) -> Iterator:
        node = self.head
        while node:
            yield node.value
            node = node.next

    def __len__(self):
        return self.size


class Stack:
    """Linked LIFO stack; O(1) push/pop."""

    def __init__(self):
        self.top = None
        self.size = 0

    def push(self, value):
        self.top = Node(value, self.top)
        self.size += 1

    def pop(self):
        if not self.top:
            raise ValueError("Stack is empty.")
        value = self.top.value
        self.top = self.top.next
        self.size -= 1
        return value

    def peek(self):
        if not self.top:
            raise ValueError("Stack is empty.")
        return self.top.value

    def __iter__(self):
        node = self.top
        while node:
            yield node.value
            node = node.next

    def __len__(self):
        return self.size


class Queue:
    """Linked FIFO queue; O(1) enqueue/dequeue."""

    def __init__(self):
        self.items = LinkedList()

    def enqueue(self, value):
        self.items.append(value)

    def dequeue(self):
        if not self.items.head:
            raise ValueError("Queue is empty.")
        value = self.items.head.value
        self.items.head = self.items.head.next
        self.items.size -= 1
        if not self.items.head:
            self.items.tail = None
        return value

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)


def expression_demo(expression):
    """Shunting-yard conversion and stack-based postfix evaluation.

    Supports nonnegative numeric literals, + - * / and parentheses.
    Unary signs and exponentiation are outside this introductory exercise.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Enter an arithmetic expression.")
    if len(expression) > 200:
        raise ValueError("Use an expression of at most 200 characters.")
    tokens = re.findall(r"\d+(?:\.\d+)?|\.\d+|[()+*/-]", expression)
    if "".join(tokens) != re.sub(r"\s+", "", expression):
        raise ValueError("Only numbers, +, -, *, / and parentheses are supported.")
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2}
    operators, output, trace = Stack(), [], []
    expect_operand = True
    for token in tokens:
        if token[0].isdigit() or token[0] == ".":
            if not expect_operand:
                raise ValueError("Insert an operator between numbers or parentheses.")
            output.append(token)
            expect_operand = False
        elif token == "(":
            if not expect_operand:
                raise ValueError("Insert an operator before '('.")
            operators.push(token)
        elif token == ")":
            if expect_operand:
                raise ValueError("Missing value before ')'.")
            while len(operators) and operators.peek() != "(":
                output.append(operators.pop())
            if not len(operators):
                raise ValueError("Parentheses do not match.")
            operators.pop()
        else:
            if expect_operand:
                raise ValueError("Expected a number; unary signs are not supported.")
            while (len(operators) and operators.peek() != "("
                   and precedence[operators.peek()] >= precedence[token]):
                output.append(operators.pop())
            operators.push(token)
            expect_operand = True
        trace.append({"token": token, "output": " ".join(output),
                      "operator_top": operators.peek() if len(operators) else "empty"})
    if expect_operand:
        raise ValueError("The expression must end with a value.")
    while len(operators):
        token = operators.pop()
        if token == "(":
            raise ValueError("Parentheses do not match.")
        output.append(token)
    values = Stack()
    for token in output:
        if token not in precedence:
            values.push(float(token))
            continue
        right, left = values.pop(), values.pop()
        if token == "/" and right == 0:
            raise ValueError("Division by zero is not allowed.")
        result = {"+": lambda: left + right, "-": lambda: left - right,
                  "*": lambda: left * right, "/": lambda: left / right}[token]()
        if not math.isfinite(result):
            raise ValueError("The result is too large.")
        values.push(result)
    return {"postfix": " ".join(output), "result": values.pop(), "trace": trace}


def compare_sums(values):
    """Count operations instead of using misleading microtiming comparisons."""
    total = 0
    for value in values:
        total += value

    def recursive(index):
        if index == len(values):
            return 0
        return values[index] + recursive(index + 1)

    return {"iterative_sum": round(total, 4), "recursive_sum": round(recursive(0), 4),
            "additions": len(values), "recursive_calls": len(values) + 1,
            "iterative_space": "O(1)", "recursive_space": "O(n)", "time": "O(n)"}


@dataclass
class TreeNode:
    value: Any
    left: "TreeNode | None" = None
    right: "TreeNode | None" = None


class BinarySearchTree:
    """A binary hierarchy ordered by case-insensitive food name."""

    def __init__(self):
        self.root = None

    def insert(self, food):
        node = TreeNode(food)
        if not self.root:
            self.root = node
            return
        current = self.root
        while True:
            side = "left" if food.name.casefold() < current.value.name.casefold() else "right"
            if getattr(current, side) is None:
                setattr(current, side, node)
                return
            current = getattr(current, side)

    def traverse(self, order="inorder"):
        if order not in {"inorder", "preorder", "postorder"}:
            raise ValueError("Choose inorder, preorder or postorder.")
        output = []

        def visit(node):
            if not node:
                return
            if order == "preorder":
                output.append(node.value.name)
            visit(node.left)
            if order == "inorder":
                output.append(node.value.name)
            visit(node.right)
            if order == "postorder":
                output.append(node.value.name)

        visit(self.root)
        return output

    def hierarchy(self):
        def serialize(node):
            if not node:
                return None
            return {"name": node.value.name, "left": serialize(node.left),
                    "right": serialize(node.right)}
        return serialize(self.root)


def balanced_food_tree(foods):
    ordered = sorted(foods, key=lambda food: food.name.casefold())
    tree = BinarySearchTree()

    def insert_middle(lo, hi):
        if lo >= hi:
            return
        middle = (lo + hi) // 2
        tree.insert(ordered[middle])
        insert_middle(lo, middle)
        insert_middle(middle + 1, hi)

    insert_middle(0, len(ordered))
    return tree


def binary_search(ordered, target):
    """Search an already sorted random-access array, not a linked list."""
    low, high, steps = 0, len(ordered) - 1, []
    target = target.strip().casefold()
    while low <= high:
        middle = (low + high) // 2
        food = ordered[middle]
        steps.append({"low": low, "mid": middle, "high": high, "name": food.name})
        if food.name.casefold() == target:
            return {"found": food.to_dict(), "steps": steps}
        if food.name.casefold() < target:
            low = middle + 1
        else:
            high = middle - 1
    return {"found": None, "steps": steps}


def linear_search(items, target):
    target = target.strip().casefold()
    steps = []
    for index, food in enumerate(items):
        matched = food.name.casefold() == target
        steps.append({"index": index, "name": food.name, "matched": matched})
        if matched:
            return {"found": food.to_dict(), "index": index, "steps": steps}
    return {"found": None, "index": None, "steps": steps}


def merge_sort(values, key=lambda value: value, reverse=False):
    items = list(values)
    buffer = items.copy()
    steps, comparisons = [], 0

    def merge(low, high):
        nonlocal comparisons
        if high - low < 2:
            return
        middle = (low + high) // 2
        merge(low, middle)
        merge(middle, high)
        left, right = low, middle
        for position in range(low, high):
            take_left = right == high
            if left < middle and right < high:
                comparisons += 1
                take_left = key(items[left]) >= key(items[right]) if reverse else key(items[left]) <= key(items[right])
            if left < middle and take_left:
                buffer[position] = items[left]
                left += 1
            else:
                buffer[position] = items[right]
                right += 1
        items[low:high] = buffer[low:high]
        steps.append({"low": low, "middle": middle, "high": high, "items": items.copy()})

    merge(0, len(items))
    return {"items": items, "steps": steps, "comparisons": comparisons}


class MaxHeap:
    """Array-backed priority queue; equal priorities preserve insertion order."""

    def __init__(self):
        self.items = []
        self.next_order = 0

    def __len__(self):
        return len(self.items)

    def snapshot(self):
        return [entry.copy() for entry in self.items]

    def higher(self, first, second):
        return (first["priority"], -first["order"]) > (second["priority"], -second["order"])

    def peek(self):
        if not self.items:
            raise ValueError("Priority queue is empty.")
        return self.items[0].copy()

    def push(self, value, priority):
        if isinstance(priority, bool) or not isinstance(priority, (int, float)) or not math.isfinite(priority):
            raise ValueError("Priority must be a finite number.")
        self.items.append({"value": value, "priority": priority, "order": self.next_order})
        self.next_order += 1
        steps = [{"action": "Append at leaf", "items": self.snapshot()}]
        index = len(self.items) - 1
        while index:
            parent = (index - 1) // 2
            if not self.higher(self.items[index], self.items[parent]):
                break
            self.items[index], self.items[parent] = self.items[parent], self.items[index]
            steps.append({"action": f"Sift up: {index} -> {parent}", "items": self.snapshot()})
            index = parent
        return steps

    def pop(self):
        removed = self.peek()
        last = self.items.pop()
        if self.items:
            self.items[0] = last
        steps = [{"action": "Remove root; move last leaf to root", "items": self.snapshot()}]
        index = 0
        while 2 * index + 1 < len(self.items):
            child = 2 * index + 1
            if child + 1 < len(self.items) and self.higher(self.items[child + 1], self.items[child]):
                child += 1
            if not self.higher(self.items[child], self.items[index]):
                break
            self.items[index], self.items[child] = self.items[child], self.items[index]
            steps.append({"action": f"Sift down: {index} -> {child}", "items": self.snapshot()})
            index = child
        return {"removed": removed, "steps": steps}


def bfs(adjacency, start, *, trace=False):
    if start not in adjacency:
        raise ValueError("Choose a food in the graph.")
    pending, visited, order, edges = Queue(), {start}, [], []
    pending.enqueue(start)
    steps = [{"current": None, "queue": list(pending), "discovered": [start]}] if trace else []
    while len(pending):
        current = pending.dequeue()
        order.append(current)
        discovered = []
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                pending.enqueue(neighbor)
                edges.append([current, neighbor])
                discovered.append(neighbor)
        if trace:
            steps.append({"current": current, "queue": list(pending), "discovered": discovered})
    result = {"order": order, "discovery_edges": edges}
    if trace:
        result["steps"] = steps
    return result