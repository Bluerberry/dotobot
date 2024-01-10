
# Native libraries
import re as regex
from typing import Any, Tuple

# Constants
MIN_RELATIVE_OVERLAP = 0.5
FUZZY_OVERLAP_MARGIN = 1
MAX_RELATIVE_DISTANCE = 0.5
FUZZY_DISTANCE_MARGIN = 3


# ---------------------> External Classes


class SearchItem:
	def __init__(self, item: Any, text: str) -> None:
		self.item = item
		self.text = text

		self.sanitized         = None
		self.overlap           = None
		self.relative_overlap  = None
		self.distance          = None
		self.relative_distance = None
		self.ranking           = None


# ---------------------> Internal Functions


def __sanitize(input: str) -> str:
		output = input.lower()
		filter = regex.compile('[^\w ]')
		return filter.sub('', output)

def __overlap(a: str, b: str) -> int:
		m, n, best = len(a), len(b), 0
		lengths = [[0 for _ in range(n + 1)] for _ in range(2)]

		# Dynamic programming shenanigans keeping track of longest suffix
		for i in range(1, m + 1):
			for j in range(1, n + 1):
				if a[i - 1] == b[j - 1]:
					lengths[i % 2][j] = lengths[(i - 1) % 2][j - 1] + 1
					if lengths[i % 2][j] > best:
						best = lengths[i % 2][j]
				else:
					lengths[i % 2][j] = 0

		return best

def __distance(a: str, b: str) -> int:
		m, n = len(a), len(b)
		prev = [i for i in range(n + 1)]
		curr = [0 for _ in range(n + 1)]

		# Dynamic programming shenanigans
		for i in range(m):
			curr[0] = i + 1

			# Find edit cost
			for j in range(n):
				del_cost = prev[j + 1] + 1
				ins_cost = curr[j] + 1
				sub_cost = prev[j] + int(a[i] != b[j])
				curr[j + 1] = min(del_cost, ins_cost, sub_cost)

			# Copy curr to prev
			for j in range(n + 1):
				prev[j] = curr[j]

		return prev[n]


# ---------------------> External Functions


def fuzzy_search(options: list[SearchItem], query: str) -> Tuple[bool, list[SearchItem]]:
	# Sorts a list of options based on overlap with, and distance to the given query
	#   - options is a list of strings to match the query to
	#   - query is a string of non-zero length
	#   - Return type is an ordered list of dictionaries with the fields { name, sanitized, overlap, distance }
	#   - The return type is ordered first by the largest overlap, then by the smallest distance

	# Sanitize input
	if len(options) < 1:
		return True, []

	# Calculate scores
	for option in options:
		option.sanitized = __sanitize(option.text)
		option.overlap = __overlap(query, option.sanitized)
		option.relative_overlap = option.overlap / len(option.sanitized)
		option.distance = __distance(query, option.sanitized)
		option.relative_distance = option.distance / len(option.sanitized)

	# Sort options
	options.sort(key=lambda option: option.distance)
	options.sort(key=lambda option: option.overlap, reverse=True)

	for ranking, option in enumerate(options, start=1):
		option.ranking = ranking

	# Check if options are conclusive
	conclusive = options[0].relative_overlap > MIN_RELATIVE_OVERLAP and                \
				 options[0].relative_distance < MAX_RELATIVE_DISTANCE and (            \
					 len(options) < 2 or                                               \
					 options[0].overlap > options[1].overlap + FUZZY_OVERLAP_MARGIN or \
					 options[0].distance < options[1].distance - FUZZY_DISTANCE_MARGIN \
				 )

	return conclusive, options