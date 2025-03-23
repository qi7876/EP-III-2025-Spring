#ifndef OUTPUT_HH
#define OUTPUT_HH

#include "linear_list.hh"

void output_to_stdout(LIST list);
void output_to_file(LIST list, const char* filename);
void output_to_csv(LIST list, const char* filename);
void output_to_email(LIST list, const char* config_path);

#endif // OUTPUT_HH
