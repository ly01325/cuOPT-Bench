\ A tiny production-scheduling MIP, only for smoke-testing the scripts (3 products, 4 periods).
\ Maximise fulfilled demand; batches are integers; a setup binary switches a product on in a period.
Maximize
 obj: 100 f_a + 100 f_b + 100 f_c
Subject To
 cap_1: 2 b_a_1 + 3 b_b_1 + 4 b_c_1 <= 40
 cap_2: 2 b_a_2 + 3 b_b_2 + 4 b_c_2 <= 40
 cap_3: 2 b_a_3 + 3 b_b_3 + 4 b_c_3 <= 40
 cap_4: 2 b_a_4 + 3 b_b_4 + 4 b_c_4 <= 40
 link_a_1: b_a_1 - 10 y_a_1 <= 0
 link_a_2: b_a_2 - 10 y_a_2 <= 0
 link_a_3: b_a_3 - 10 y_a_3 <= 0
 link_a_4: b_a_4 - 10 y_a_4 <= 0
 link_b_1: b_b_1 - 10 y_b_1 <= 0
 link_b_2: b_b_2 - 10 y_b_2 <= 0
 link_b_3: b_b_3 - 10 y_b_3 <= 0
 link_b_4: b_b_4 - 10 y_b_4 <= 0
 link_c_1: b_c_1 - 10 y_c_1 <= 0
 link_c_2: b_c_2 - 10 y_c_2 <= 0
 link_c_3: b_c_3 - 10 y_c_3 <= 0
 link_c_4: b_c_4 - 10 y_c_4 <= 0
 setups: y_a_1 + y_a_2 + y_a_3 + y_a_4 + y_b_1 + y_b_2 + y_b_3 + y_b_4 + y_c_1 + y_c_2 + y_c_3 + y_c_4 <= 9
 ful_a: f_a - b_a_1 - b_a_2 - b_a_3 - b_a_4 <= 0
 ful_b: f_b - b_b_1 - b_b_2 - b_b_3 - b_b_4 <= 0
 ful_c: f_c - b_c_1 - b_c_2 - b_c_3 - b_c_4 <= 0
 dem_a: f_a <= 30
 dem_b: f_b <= 20
 dem_c: f_c <= 12
Bounds
 0 <= f_a
 0 <= f_b
 0 <= f_c
General
 b_a_1 b_a_2 b_a_3 b_a_4 b_b_1 b_b_2 b_b_3 b_b_4 b_c_1 b_c_2 b_c_3 b_c_4
Binary
 y_a_1 y_a_2 y_a_3 y_a_4 y_b_1 y_b_2 y_b_3 y_b_4 y_c_1 y_c_2 y_c_3 y_c_4
End
