"""Unit tests for board_state.geometry: cell centres and sphere containment, per grid type."""

from board_state.geometry import cell_centre_ft, cells_in_shape


def test_square_cell_centre_is_half_a_cell_into_the_cell() -> None:
    assert cell_centre_ft(5, 5, "square") == (27.5, 27.5)


def test_square_five_foot_sphere_on_a_cell_covers_the_cross_of_five_cells() -> None:
    cells = cells_in_shape(20, 20, "sphere", 5, 5, radius_ft=5.0, grid_type="square")

    assert sorted(cells) == [[4, 5], [5, 4], [5, 5], [5, 6], [6, 5]]


def test_square_twenty_foot_sphere_covers_forty_nine_cells() -> None:
    cells = cells_in_shape(20, 20, "sphere", 5, 5, radius_ft=20.0, grid_type="square")

    assert len(cells) == 49


def test_hex_cell_centre_offsets_odd_rows_by_half_a_column() -> None:
    even_x, _ = cell_centre_ft(2, 2, "hex")
    odd_x, _ = cell_centre_ft(2, 3, "hex")

    assert odd_x > even_x


def test_hex_five_foot_sphere_covers_the_origin_and_its_six_neighbours_on_an_even_row() -> None:
    cells = cells_in_shape(10, 10, "sphere", 2, 2, radius_ft=5.0, grid_type="hex")

    assert sorted(cells) == sorted([[2, 2], [1, 2], [3, 2], [1, 1], [2, 1], [1, 3], [2, 3]])


def test_hex_five_foot_sphere_covers_the_origin_and_its_six_neighbours_on_an_odd_row() -> None:
    cells = cells_in_shape(10, 10, "sphere", 2, 3, radius_ft=5.0, grid_type="hex")

    assert sorted(cells) == sorted([[2, 3], [1, 3], [3, 3], [2, 2], [3, 2], [2, 4], [3, 4]])
