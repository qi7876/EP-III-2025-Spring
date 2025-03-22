#include "../include/linear_list.hh"
#include <stdio.h>

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
                // Correct swap implementation
                list_delete(list, j);
                list_delete(list, j); // After first delete, j+1 becomes j
                list_insert(list, j, val1);
                list_insert(list, j, val2);
            }
        }
    }
}

void print_list(LIST list) {
    int length = list_length(list);
    printf("List: ");
    for (int i = 0; i < length; i++) {
        printf("%d ", list_get(list, i));
    }
    printf("\n");
}

int main() {
    LIST myList = create_list();

    list_insert(myList, 0, 5);
    list_insert(myList, 1, 2);
    list_insert(myList, 2, 8);
    list_insert(myList, 3, 1);
    list_insert(myList, 4, 9);
    list_insert(myList, 5, 4);

    printf("Before Sorting:\n");
    print_list(myList);
    bubble_sort_list(myList);
    printf("After Sorting:\n");
    print_list(myList);

    return 0;
}