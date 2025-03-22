#include "../include/output.hh"
#include <cstdio>

void output_to_stdout(LIST list) {
    int length = list_length(list);
    for (int i = 0; i < length; i++) {
        printf("%d ", list_get(list, i));
    }
    printf("\n");
}

void output_to_file(LIST list, const char* filename) {
    FILE *fp = fopen(filename, "w");
    if (!fp) {
         fprintf(stderr, "Error: Could not open file %s for writing\n", filename);
         return;
    }
    int length = list_length(list);
    for (int i = 0; i < length; i++){
         fprintf(fp, "%d\n", list_get(list, i));
    }
    fclose(fp);
}

void output_to_csv(LIST list, const char* filename) {
    FILE *fp = fopen(filename, "w");
    if (!fp) {
         fprintf(stderr, "Error: Could not open file %s for writing\n", filename);
         return;
    }
    int length = list_length(list);
    for (int i = 0; i < length; i++){
         fprintf(fp, "%d", list_get(list, i));
         if (i != length - 1)
              fprintf(fp, ",");
    }
    fprintf(fp, "\n");
    fclose(fp);
}