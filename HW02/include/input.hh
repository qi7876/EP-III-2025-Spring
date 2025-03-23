#ifndef INPUT_HH
#define INPUT_HH

#include "linear_list.hh"

LIST read_from_txt(const char* file_path);
LIST read_from_csv(const char* file_path);
LIST read_from_stdin();

#endif // INPUT_HH
