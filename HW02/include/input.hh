#ifndef INPUT_HH
#define INPUT_HH

#include "linear_list.hh"

#ifdef __cplusplus
extern "C" {
#endif

LIST read_from_txt(const char* file_path);
LIST read_from_csv(const char* file_path);
LIST read_from_stdin();

#ifdef __cplusplus
}
#endif

#endif // INPUT_HH