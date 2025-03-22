#include "../include/linear_list.hh"
#include <iostream>

// 定义链表节点结构体
typedef struct node_t {
    int data;
    struct node_t* next;
} node_t;

// 定义线性表结构体 (使用链表实现)
struct list_t {
    node_t* head;
    int length;
};

LIST create_list() {
    // TODO:
    std::cout << "[DEBUG] Using Linked List" << std::endl;
    LIST newList = (LIST)malloc(sizeof(struct list_t));
    if (newList == nullptr) {
        return nullptr;
    }
    newList->head = nullptr;
    newList->length = 0;
    return newList;
}

int list_length(LIST list) {
    if (list == nullptr) {
        return 0;
    }
    return list->length;
}

int list_get(LIST list, int pos) {
    if (list == nullptr || pos < 0 || pos >= list->length) {
        return E_NODE_NOT_FOUND;
    }

    node_t* current = list->head;
    for (int i = 0; i < pos; i++) {
        current = current->next;
    }

    return current->data;
}

int list_insert(LIST list, int pos, int x) {
    if (list == nullptr || pos < 0 || pos > list->length) {
        return E_NODE_NOT_FOUND;
    }

    node_t* newNode = (node_t*)malloc(sizeof(node_t));
    if (newNode == nullptr) {
        return -2; // 内存分配失败
    }
    newNode->data = x;
    newNode->next = nullptr;

    if (pos == 0) {
        newNode->next = list->head;
        list->head = newNode;
    } else {
        node_t* current = list->head;
        for (int i = 0; i < pos - 1; i++) {
            current = current->next;
        }
        newNode->next = current->next;
        current->next = newNode;
    }
    list->length++;
    return E_SUCCESS;
}

int list_delete(LIST list, int pos) {
    if (list == nullptr || list->head == nullptr || pos < 0 || pos >= list->length) {
        return E_NODE_NOT_FOUND;
    }

    node_t* deletedNode = nullptr;
    if (pos == 0) {
        deletedNode = list->head;
        list->head = list->head->next;
    } else {
        node_t* current = list->head;
        for (int i = 0; i < pos - 1; i++) {
            current = current->next;
        }
        deletedNode = current->next;
        current->next = current->next->next;
    }

    if (deletedNode != nullptr) {
        free(deletedNode);
        list->length--;
        return E_SUCCESS;
    } else {
        return E_NODE_NOT_FOUND;
    }
}