#include "../include/linear_list.hh"
#include <cstdlib>

// bubble sort
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

static int partition(LIST list, int low, int high) {
    int pivot = list_get(list, high);
    int i = low - 1;

    for (int j = low; j < high; j++) {
        if (list_get(list, j) < pivot) {
            i++;
            int val1 = list_get(list, i);
            int val2 = list_get(list, j);
            list_delete(list, i);
            list_insert(list, i, val2);
            list_delete(list, j);
            list_insert(list, j, val1);
        }
    }

    int val1 = list_get(list, i + 1);
    int val2 = list_get(list, high);
    list_delete(list, i + 1);
    list_insert(list, i + 1, val2);
    list_delete(list, high);
    list_insert(list, high, val1);

    return i + 1;
}

// quick sort
static void quick_sort_helper(LIST list, int low, int high) {
    if (low < high) {
        int pi = partition(list, low, high);
        quick_sort_helper(list, low, pi - 1);
        quick_sort_helper(list, pi + 1, high);
    }
}

void quick_sort_list(LIST list) {
    if (list == nullptr) {
        return;
    }

    int length = list_length(list);
    if (length <= 1) {
        return;
    }

    quick_sort_helper(list, 0, length - 1);
}

static void merge(LIST list, int left, int mid, int right) {
    int n1 = mid - left + 1;
    int n2 = right - mid;

    int* L = new int[n1];
    int* R = new int[n2];

    for (int i = 0; i < n1; i++) {
        L[i] = list_get(list, left + i);
    }
    for (int i = 0; i < n2; i++) {
        R[i] = list_get(list, mid + 1 + i);
    }

    int i = 0, j = 0, k = left;
    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) {
            list_delete(list, k);
            list_insert(list, k, L[i]);
            i++;
        } else {
            list_delete(list, k);
            list_insert(list, k, R[j]);
            j++;
        }
        k++;
    }

    while (i < n1) {
        list_delete(list, k);
        list_insert(list, k, L[i]);
        i++;
        k++;
    }
    while (j < n2) {
        list_delete(list, k);
        list_insert(list, k, R[j]);
        j++;
        k++;
    }

    delete[] L;
    delete[] R;
}

// merge sort
static void merge_sort_helper(LIST list, int left, int right) {
    if (left < right) {
        int mid = left + (right - left) / 2;
        merge_sort_helper(list, left, mid);
        merge_sort_helper(list, mid + 1, right);
        merge(list, left, mid, right);
    }
}

void merge_sort_list(LIST list) {
    if (list == nullptr) {
        return;
    }

    int length = list_length(list);
    if (length <= 1) {
        return;
    }

    merge_sort_helper(list, 0, length - 1);
}
