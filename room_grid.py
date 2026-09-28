import math

import cv2
import numpy as np


class PerspectiveRoomGrid:

    def __init__(self, columns=8, rows=6, downward_tilt_degrees=30.0):
        if columns < 1 or rows < 1:
            raise ValueError("Grid rows and columns must be positive")
        if not 1 <= downward_tilt_degrees <= 89:
            raise ValueError("Grid tilt must be between 1 and 89 degrees")

        self.columns = int(columns)
        self.rows = int(rows)
        self.downward_tilt_degrees = float(downward_tilt_degrees)

        tilt_radians = math.radians(self.downward_tilt_degrees)
        perspective_depth = 1.0 / math.tan(tilt_radians)
        self.row_exponent = max(1.1, min(3.0, perspective_depth))
        self.width_perspective = max(0.18, min(0.65, perspective_depth * 0.35))

    def _row_boundaries(self, height):
        return [
            height * ((index / self.rows) ** self.row_exponent)
            for index in range(self.rows + 1)
        ]

    def _x_at(self, normalized_column, y, width, height):
        base_x = normalized_column * width
        vanishing_x = width / 2.0
        top_weight = max(0.0, min(1.0, 1.0 - (y / max(height, 1))))
        convergence = self.width_perspective * top_weight
        edge_falloff = math.sin(math.pi * normalized_column)
        return base_x + convergence * edge_falloff * (vanishing_x - base_x)

    def cell_polygon(self, row, column, width, height):
        boundaries = self._row_boundaries(height)
        top_y = boundaries[row]
        bottom_y = boundaries[row + 1]
        left = column / self.columns
        right = (column + 1) / self.columns

        points = [
            (self._x_at(left, top_y, width, height), top_y),
            (self._x_at(right, top_y, width, height), top_y),
            (self._x_at(right, bottom_y, width, height), bottom_y),
            (self._x_at(left, bottom_y, width, height), bottom_y),
        ]
        return np.round(points).astype(np.int32)

    def cell_for_point(self, x, y, width, height):
        x = max(0.0, min(float(width - 1), float(x)))
        y = max(0.0, min(float(height - 1), float(y)))
        boundaries = self._row_boundaries(height)

        row = self.rows - 1
        for index in range(self.rows):
            if boundaries[index] <= y <= boundaries[index + 1]:
                row = index
                break

        column_edges = [
            self._x_at(index / self.columns, y, width, height)
            for index in range(self.columns + 1)
        ]
        column = self.columns - 1
        for index in range(self.columns):
            if column_edges[index] <= x <= column_edges[index + 1]:
                column = index
                break
        return row, column

    def occupied_cells(self, people, frame_shape):
        height, width = frame_shape[:2]
        occupied = set()
        cell_polygons = {
            (row, column): self.cell_polygon(row, column, width, height).astype(np.float32)
            for row in range(self.rows)
            for column in range(self.columns)
        }

        for box, _centroid in people:
            start_x, start_y, end_x, end_y = box
            start_x = max(0, min(width, start_x))
            start_y = max(0, min(height, start_y))
            end_x = max(0, min(width, end_x))
            end_y = max(0, min(height, end_y))
            if end_x <= start_x or end_y <= start_y:
                continue

            person_polygon = np.array(
                [
                    [start_x, start_y],
                    [end_x, start_y],
                    [end_x, end_y],
                    [start_x, end_y],
                ],
                dtype=np.float32,
            )
            for cell, polygon in cell_polygons.items():
                intersection_area, _ = cv2.intersectConvexConvex(
                    person_polygon, polygon
                )
                if intersection_area > 1.0:
                    occupied.add(cell)
        return occupied

    def draw(self, frame, occupied_cells):
        height, width = frame.shape[:2]
        overlay = frame.copy()

        for row, column in occupied_cells:
            polygon = self.cell_polygon(row, column, width, height)
            cv2.fillPoly(overlay, [polygon], (60, 190, 90))
        cv2.addWeighted(overlay, 0.30, frame, 0.70, 0, frame)

        for row in range(self.rows):
            for column in range(self.columns):
                polygon = self.cell_polygon(row, column, width, height)
                cv2.polylines(frame, [polygon], True, (220, 220, 220), 1, cv2.LINE_AA)

        for row, column in occupied_cells:
            polygon = self.cell_polygon(row, column, width, height)
            cv2.polylines(frame, [polygon], True, (40, 220, 90), 2, cv2.LINE_AA)
