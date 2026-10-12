/*
 * Minimal freestanding libc for compiling Krux's bc-ur (cUR) to wasm32.
 *
 * Only what cUR uses: a size-class allocator on top of wasm linear memory,
 * the usual mem* / str* / ctype helpers, a small printf family that covers
 * the formats cUR uses (%s %c %d %i %u %x %X %zu %lu %llu with width and
 * zero-padding) and strtoul. printf() is a no-op (debug output only).
 */
#include "kxlibc.h"

extern unsigned char __heap_base;

/* ---------------------------------------------------------------- memory */

#define NUM_CLASSES 40
#define HDR 8u

static uintptr_t heap_top = 0;
static uintptr_t heap_end = 0;
static void *free_lists[NUM_CLASSES];

static unsigned size_class(size_t n) {
  unsigned c = 4; /* 16 bytes minimum */
  while (((size_t)1 << c) < n + HDR) c++;
  return c;
}

static void *raw_alloc(size_t total) {
  if (heap_top == 0) {
    heap_top = ((uintptr_t)&__heap_base + 15u) & ~(uintptr_t)15u;
    heap_end = (uintptr_t)__builtin_wasm_memory_size(0) * 65536u;
  }
  uintptr_t p = (heap_top + 7u) & ~(uintptr_t)7u;
  while (p + total > heap_end) {
    size_t need = (p + total - heap_end + 65535u) / 65536u;
    if (__builtin_wasm_memory_grow(0, need) == (size_t)-1) return NULL;
    heap_end = (uintptr_t)__builtin_wasm_memory_size(0) * 65536u;
  }
  heap_top = p + total;
  return (void *)p;
}

void *malloc(size_t n) {
  unsigned c = size_class(n);
  if (c >= NUM_CLASSES) return NULL;
  void *blk = free_lists[c];
  if (blk) {
    free_lists[c] = *(void **)((char *)blk + HDR);
  } else {
    blk = raw_alloc((size_t)1 << c);
    if (!blk) return NULL;
  }
  *(uint32_t *)blk = c;
  *((uint32_t *)blk + 1) = 0x4B525558u; /* "KRUX" */
  return (char *)blk + HDR;
}

void free(void *p) {
  if (!p) return;
  char *blk = (char *)p - HDR;
  if (*((uint32_t *)blk + 1) != 0x4B525558u) return; /* not ours / double free */
  unsigned c = *(uint32_t *)blk;
  *((uint32_t *)blk + 1) = 0;
  *(void **)p = free_lists[c];
  free_lists[c] = blk;
}

void *calloc(size_t n, size_t m) {
  size_t t = n * m;
  if (m && t / m != n) return NULL;
  void *p = malloc(t);
  if (p) memset(p, 0, t);
  return p;
}

void *realloc(void *p, size_t n) {
  if (!p) return malloc(n);
  if (n == 0) { free(p); return NULL; }
  char *blk = (char *)p - HDR;
  unsigned c = *(uint32_t *)blk;
  size_t cap = ((size_t)1 << c) - HDR;
  if (n <= cap) return p;
  void *q = malloc(n);
  if (!q) return NULL;
  memcpy(q, p, cap);
  free(p);
  return q;
}

void abort(void) { __builtin_trap(); }

/* ---------------------------------------------------------------- mem/str */

void *memcpy(void *d, const void *s, size_t n) {
  unsigned char *dd = d; const unsigned char *ss = s;
  while (n--) *dd++ = *ss++;
  return d;
}
void *memmove(void *d, const void *s, size_t n) {
  unsigned char *dd = d; const unsigned char *ss = s;
  if (dd == ss || n == 0) return d;
  if (dd < ss) { while (n--) *dd++ = *ss++; }
  else { dd += n; ss += n; while (n--) *--dd = *--ss; }
  return d;
}
void *memset(void *d, int c, size_t n) {
  unsigned char *dd = d;
  while (n--) *dd++ = (unsigned char)c;
  return d;
}
int memcmp(const void *a, const void *b, size_t n) {
  const unsigned char *x = a, *y = b;
  for (; n; n--, x++, y++) if (*x != *y) return *x - *y;
  return 0;
}
size_t strlen(const char *s) { const char *p = s; while (*p) p++; return (size_t)(p - s); }
int strcmp(const char *a, const char *b) {
  while (*a && *a == *b) { a++; b++; }
  return (unsigned char)*a - (unsigned char)*b;
}
int strncmp(const char *a, const char *b, size_t n) {
  for (; n; n--, a++, b++) {
    if (*a != *b) return (unsigned char)*a - (unsigned char)*b;
    if (!*a) return 0;
  }
  return 0;
}
char *strcpy(char *d, const char *s) { char *r = d; while ((*d++ = *s++)); return r; }
char *strncpy(char *d, const char *s, size_t n) {
  size_t i = 0;
  for (; i < n && s[i]; i++) d[i] = s[i];
  for (; i < n; i++) d[i] = 0;
  return d;
}
char *strcat(char *d, const char *s) { strcpy(d + strlen(d), s); return d; }
char *strchr(const char *s, int c) {
  for (;; s++) { if (*s == (char)c) return (char *)s; if (!*s) return NULL; }
}
char *strrchr(const char *s, int c) {
  const char *r = NULL;
  for (;; s++) { if (*s == (char)c) r = s; if (!*s) return (char *)r; }
}
char *strdup(const char *s) {
  size_t n = strlen(s) + 1;
  char *d = malloc(n);
  if (d) memcpy(d, s, n);
  return d;
}

int isdigit(int c) { return c >= '0' && c <= '9'; }
int islower(int c) { return c >= 'a' && c <= 'z'; }
int isupper(int c) { return c >= 'A' && c <= 'Z'; }
int isalpha(int c) { return islower(c) || isupper(c); }
int isalnum(int c) { return isalpha(c) || isdigit(c); }
int isspace(int c) { return c == ' ' || (c >= '\t' && c <= '\r'); }
int isxdigit(int c) { return isdigit(c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'); }
int tolower(int c) { return isupper(c) ? c + 32 : c; }
int toupper(int c) { return islower(c) ? c - 32 : c; }

unsigned long strtoul(const char *s, char **end, int base) {
  const char *p = s;
  unsigned long v = 0;
  int any = 0;
  while (isspace((unsigned char)*p)) p++;
  if (*p == '+') p++;
  if ((base == 0 || base == 16) && p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) {
    p += 2; base = 16;
  } else if (base == 0) {
    base = (*p == '0') ? 8 : 10;
  }
  for (;; p++) {
    int d;
    if (isdigit((unsigned char)*p)) d = *p - '0';
    else if (*p >= 'a' && *p <= 'z') d = *p - 'a' + 10;
    else if (*p >= 'A' && *p <= 'Z') d = *p - 'A' + 10;
    else break;
    if (d >= base) break;
    v = v * (unsigned long)base + (unsigned long)d;
    any = 1;
  }
  if (end) *end = (char *)(any ? p : s);
  return v;
}
long strtol(const char *s, char **end, int base) {
  const char *p = s;
  while (isspace((unsigned char)*p)) p++;
  int neg = 0;
  if (*p == '-') { neg = 1; p++; }
  char *e;
  unsigned long v = strtoul(p, &e, base);
  if (end) *end = (e == p) ? (char *)s : e;
  return neg ? -(long)v : (long)v;
}
int atoi(const char *s) { return (int)strtol(s, NULL, 10); }

/* ---------------------------------------------------------------- printf */

typedef struct { char *buf; size_t cap; size_t len; } out_t;

static void put(out_t *o, char c) {
  if (o->buf && o->len + 1 < o->cap) o->buf[o->len] = c;
  o->len++;
}

static void put_num(out_t *o, unsigned long long v, int base, int upper,
                    int neg, int width, int zero) {
  char tmp[32];
  int n = 0;
  const char *dig = upper ? "0123456789ABCDEF" : "0123456789abcdef";
  do { tmp[n++] = dig[v % (unsigned)base]; v /= (unsigned)base; } while (v);
  int len = n + (neg ? 1 : 0);
  if (!zero) while (width-- > len) put(o, ' ');
  if (neg) put(o, '-');
  if (zero) while (width-- > len) put(o, '0');
  while (n) put(o, tmp[--n]);
}

int vsnprintf(char *buf, size_t cap, const char *fmt, va_list ap) {
  out_t o = { buf, cap, 0 };
  for (const char *f = fmt; *f; f++) {
    if (*f != '%') { put(&o, *f); continue; }
    f++;
    int zero = 0, width = 0, lng = 0, size_t_mod = 0;
    if (*f == '%') { put(&o, '%'); continue; }
    while (*f == '0') { zero = 1; f++; }
    while (isdigit((unsigned char)*f)) { width = width * 10 + (*f - '0'); f++; }
    while (*f == 'l') { lng++; f++; }
    if (*f == 'z') { size_t_mod = 1; f++; }
    switch (*f) {
      case 's': {
        const char *s = va_arg(ap, const char *);
        if (!s) s = "(null)";
        int l = (int)strlen(s);
        while (width-- > l) put(&o, ' ');
        while (*s) put(&o, *s++);
        break;
      }
      case 'c': put(&o, (char)va_arg(ap, int)); break;
      case 'd': case 'i': {
        long long v;
        if (lng >= 2) v = va_arg(ap, long long);
        else if (lng == 1) v = va_arg(ap, long);
        else if (size_t_mod) v = (long long)va_arg(ap, size_t);
        else v = va_arg(ap, int);
        int neg = v < 0;
        put_num(&o, neg ? (unsigned long long)(-v) : (unsigned long long)v, 10, 0, neg, width, zero);
        break;
      }
      case 'u': case 'x': case 'X': {
        unsigned long long v;
        if (lng >= 2) v = va_arg(ap, unsigned long long);
        else if (lng == 1) v = va_arg(ap, unsigned long);
        else if (size_t_mod) v = va_arg(ap, size_t);
        else v = va_arg(ap, unsigned int);
        put_num(&o, v, *f == 'u' ? 10 : 16, *f == 'X', 0, width, zero);
        break;
      }
      default:
        put(&o, '%');
        if (*f) put(&o, *f); else f--;
    }
  }
  if (o.buf && o.cap) o.buf[o.len < o.cap ? o.len : o.cap - 1] = 0;
  return (int)o.len;
}

int snprintf(char *buf, size_t n, const char *fmt, ...) {
  va_list ap; va_start(ap, fmt);
  int r = vsnprintf(buf, n, fmt, ap);
  va_end(ap);
  return r;
}
int sprintf(char *buf, const char *fmt, ...) {
  va_list ap; va_start(ap, fmt);
  int r = vsnprintf(buf, (size_t)-1 / 2, fmt, ap);
  va_end(ap);
  return r;
}
int printf(const char *fmt, ...) { (void)fmt; return 0; }

/* ---------------------------------------------------------------- math */

double ceil(double x) { return __builtin_ceil(x); }
double floor(double x) { return __builtin_floor(x); }
double log(double x) {
  /* ln(x) via frexp-style decomposition and atanh series; only needed for
     completeness (cUR does not call it on the code paths Krux uses). */
  if (x <= 0) return -1.0 / 0.0;
  int e = 0;
  while (x > 2.0) { x /= 2.0; e++; }
  while (x < 1.0) { x *= 2.0; e--; }
  double y = (x - 1.0) / (x + 1.0), y2 = y * y, term = y, sum = 0;
  for (int k = 1; k < 60; k += 2) { sum += term / k; term *= y2; }
  return 2.0 * sum + e * 0.69314718055994530942;
}

void *memchr(const void *s, int c, size_t n) {
  const unsigned char *p = s;
  for (; n; n--, p++) if (*p == (unsigned char)c) return (void *)p;
  return NULL;
}
char *strstr(const char *h, const char *n) {
  size_t l = strlen(n);
  if (!l) return (char *)h;
  for (; *h; h++) if (!strncmp(h, n, l)) return (char *)h;
  return NULL;
}
size_t strnlen(const char *s, size_t n) { size_t i = 0; while (i < n && s[i]) i++; return i; }
char *strndup(const char *s, size_t n) {
  size_t l = strnlen(s, n);
  char *d = malloc(l + 1);
  if (d) { memcpy(d, s, l); d[l] = 0; }
  return d;
}
