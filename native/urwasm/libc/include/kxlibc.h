/* Minimal freestanding libc for compiling Krux's bc-ur (cUR) to wasm32. */
#ifndef KXLIBC_H
#define KXLIBC_H
#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdbool.h>

void *malloc(size_t n);
void *calloc(size_t n, size_t m);
void *realloc(void *p, size_t n);
void free(void *p);
void abort(void);
unsigned long strtoul(const char *s, char **end, int base);
long strtol(const char *s, char **end, int base);
int atoi(const char *s);

void *memcpy(void *d, const void *s, size_t n);
void *memmove(void *d, const void *s, size_t n);
void *memset(void *d, int c, size_t n);
int memcmp(const void *a, const void *b, size_t n);
void *memchr(const void *s, int c, size_t n);
char *strstr(const char *h, const char *n);
char *strndup(const char *s, size_t n);
size_t strnlen(const char *s, size_t n);
size_t strlen(const char *s);
int strcmp(const char *a, const char *b);
int strncmp(const char *a, const char *b, size_t n);
char *strcpy(char *d, const char *s);
char *strncpy(char *d, const char *s, size_t n);
char *strcat(char *d, const char *s);
char *strchr(const char *s, int c);
char *strrchr(const char *s, int c);
char *strdup(const char *s);

int isdigit(int c);
int isalpha(int c);
int isalnum(int c);
int isspace(int c);
int isxdigit(int c);
int islower(int c);
int isupper(int c);
int tolower(int c);
int toupper(int c);

int vsnprintf(char *buf, size_t n, const char *fmt, va_list ap);
int snprintf(char *buf, size_t n, const char *fmt, ...);
int sprintf(char *buf, const char *fmt, ...);
int printf(const char *fmt, ...);

double ceil(double x);
double floor(double x);
double log(double x);
#endif
