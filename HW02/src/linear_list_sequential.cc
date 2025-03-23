#include "../include/linear_list.hh"
#include <cstdlib>
#define INITIAL_CAPACITY 100

// 内部结构体，顺序表实现
struct list_t {
    int* data; // 存储线性表元素的数组
    int length; // 当前元素数量
    int capacity; // 数组容量
};

// 创建一个空的线性表
LIST create_list() {
    LIST list = (LIST)malloc(sizeof(struct list_t));
    if (!list)
        return NULL;
    list->data = (int*)malloc(INITIAL_CAPACITY * sizeof(int));
    if (!list->data) {
        free(list);
        return NULL;
    }
    list->length = 0;
    list->capacity = INITIAL_CAPACITY;
    return list;
}

// 获取线性表的长度
int list_length(LIST list) {
    if (!list)
        return 0;
    return list->length;
}

// 获取指定位置上的节点，不存在则返回 E_NODE_NOT_FOUND
int list_get(LIST list, int pos) {
    if (!list || pos < 0 || pos >= list->length)
        return E_NODE_NOT_FOUND;
    return list->data[pos];
}

// 内部函数：保证表有足够的容量，若满则扩充
static int ensure_capacity(LIST list) {
    if (list->length >= list->capacity) {
        int new_capacity = list->capacity * 2;
        int* new_data = (int*)realloc(list->data, new_capacity * sizeof(int));
        if (!new_data)
            return -1;
        list->data = new_data;
        list->capacity = new_capacity;
    }
    return 0;
}

// 将数值 x 插入到线性表的位置 pos 上
int list_insert(LIST list, int pos, int x) {
    if (!list || pos < 0 || pos > list->length)
        return E_NODE_NOT_FOUND;
    if (ensure_capacity(list) != 0) {
        return -1; // 内存分配失败
    }
    // 从后向前移动数据，为插入空出位置
    for (int i = list->length; i > pos; --i) {
        list->data[i] = list->data[i - 1];
    }
    list->data[pos] = x;
    list->length++;
    return E_SUCCESS;
}

// 删除线性表中指定位置上的节点，位置不存在则返回 E_NODE_NOT_FOUND
int list_delete(LIST list, int pos) {
    if (!list || pos < 0 || pos >= list->length)
        return E_NODE_NOT_FOUND;
    // 将后续元素依次前移
    for (int i = pos; i < list->length - 1; ++i) {
        list->data[i] = list->data[i + 1];
    }
    list->length--;
    return E_SUCCESS;
}

void list_destroy(LIST list) {
    if (list == nullptr) {
        return;  // 列表为空，直接返回
    }

    // 释放动态数组
    if (list->data != nullptr) {
        free(list->data);
    }

    // 释放列表结构本身
    free(list);
}