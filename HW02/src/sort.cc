#include "../include/linear_list.hh"
#include <cstddef>

void bubble_sort_list(LIST list) {
    if (list == nullptr) {
        return;
    }

    int length = list_length(list);
    if (length <= 1) {
        return;
    }

    for (int i = 0; i < length - 1; i++) {
        for (int j = 0; j < length - i - 1; j++) {
            int val1 = list_get(list, j);
            int val2 = list_get(list, j + 1);

            if (val1 > val2) {
                list_delete(list, j);
                list_delete(list, j);
                list_insert(list, j, val1);
                list_insert(list, j, val2);
            }
        }
    }
}