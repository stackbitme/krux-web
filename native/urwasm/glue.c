/*
 * Flat C API over Krux's bc-ur (cUR) library, exported from the wasm module.
 *
 * Mirrors what the CPython binding (python/uUR.c in Krux) does, so the
 * Python shim (runtime/kruxweb/uUR.py) can expose the exact same `uUR`
 * module surface on Pyodide. Every buffer returned to JS is malloc'd here and
 * must be released with kx_free().
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "src/types/bip39.h"
#include "src/types/bytes_type.h"
#include "src/types/output.h"
#include "src/types/psbt.h"
#include "src/ur.h"
#include "src/ur_decoder.h"
#include "src/ur_encoder.h"
#include "src/utils.h"

#define EXPORT(name) __attribute__((export_name(#name)))

EXPORT(kx_malloc) void *kx_malloc(size_t n) { return malloc(n ? n : 1); }
EXPORT(kx_free) void kx_free(void *p) { free(p); }

/* Out-length slot shared by the functions that return a buffer. */
static size_t g_out_len;
EXPORT(kx_out_len) size_t kx_out_len(void) { return g_out_len; }

static uint8_t *dup_bytes(const uint8_t *data, size_t len) {
  uint8_t *out = malloc(len ? len : 1);
  if (out && len) memcpy(out, data, len);
  g_out_len = len;
  return out;
}

/* ------------------------------------------------------------------- UR */

EXPORT(kx_is_ur_type) int kx_is_ur_type(const char *type) { return is_ur_type(type); }

EXPORT(kx_ur_new) ur_t *kx_ur_new(const char *type, const uint8_t *cbor, size_t len) {
  return ur_new(type, cbor, len);
}
EXPORT(kx_ur_free) void kx_ur_free(ur_t *ur) { ur_free(ur); }
EXPORT(kx_ur_type) const char *kx_ur_type(ur_t *ur) { return ur_get_type(ur); }
EXPORT(kx_ur_cbor) const uint8_t *kx_ur_cbor(ur_t *ur) { return ur_get_cbor(ur); }
EXPORT(kx_ur_cbor_len) size_t kx_ur_cbor_len(ur_t *ur) { return ur_get_cbor_len(ur); }

/* -------------------------------------------------------------- decoder */

EXPORT(kx_dec_new) ur_decoder_t *kx_dec_new(void) { return ur_decoder_new(); }
EXPORT(kx_dec_free) void kx_dec_free(ur_decoder_t *d) { ur_decoder_free(d); }
EXPORT(kx_dec_receive) int kx_dec_receive(ur_decoder_t *d, const char *part) {
  return (int)ur_decoder_receive_part(d, part);
}
EXPORT(kx_dec_state) int kx_dec_state(ur_decoder_t *d) { return (int)ur_decoder_get_state(d); }
EXPORT(kx_dec_pct) float kx_dec_pct(ur_decoder_t *d, int weighted) {
  return weighted ? ur_decoder_estimated_percent_complete_weighted(d)
                  : ur_decoder_estimated_percent_complete(d);
}
EXPORT(kx_dec_expected) size_t kx_dec_expected(ur_decoder_t *d) {
  return ur_decoder_expected_part_count(d);
}
EXPORT(kx_dec_processed) size_t kx_dec_processed(ur_decoder_t *d) {
  return ur_decoder_processed_parts_count(d);
}
/* Returns a fresh, owned ur_t copy of the decoder result, or NULL. */
EXPORT(kx_dec_result) ur_t *kx_dec_result(ur_decoder_t *d) {
  ur_result_t *r = ur_decoder_get_result(d);
  if (!r) return NULL;
  return ur_new(r->type, r->cbor_data, r->cbor_len);
}

/* -------------------------------------------------------------- encoder */

EXPORT(kx_enc_new)
ur_encoder_t *kx_enc_new(const char *type, const uint8_t *cbor, size_t len,
                         size_t max_frag, uint32_t first_seq, size_t min_frag) {
  return ur_encoder_new(type, cbor, len, max_frag, first_seq, min_frag);
}
EXPORT(kx_enc_free) void kx_enc_free(ur_encoder_t *e) { ur_encoder_free(e); }
EXPORT(kx_enc_next) char *kx_enc_next(ur_encoder_t *e) {
  char *part = NULL;
  if (!ur_encoder_next_part(e, &part)) {
    free(part);
    return NULL;
  }
  return part;
}
EXPORT(kx_enc_complete) int kx_enc_complete(ur_encoder_t *e) { return ur_encoder_is_complete(e); }
EXPORT(kx_enc_single) int kx_enc_single(ur_encoder_t *e) { return ur_encoder_is_single_part(e); }
EXPORT(kx_enc_has_fountain) int kx_enc_has_fountain(ur_encoder_t *e) {
  return e && e->fountain_encoder != NULL;
}
EXPORT(kx_enc_seq_len) size_t kx_enc_seq_len(ur_encoder_t *e) { return ur_encoder_seq_len(e); }

/* ---------------------------------------------------------------- Types */

EXPORT(kx_bytes_from_cbor) uint8_t *kx_bytes_from_cbor(const uint8_t *in, size_t len) {
  bytes_data_t *b = bytes_from_cbor(in, len);
  if (!b) return NULL;
  size_t n;
  const uint8_t *data = bytes_get_data(b, &n);
  uint8_t *out = dup_bytes(data, n);
  bytes_free(b);
  return out;
}

EXPORT(kx_bytes_to_cbor) uint8_t *kx_bytes_to_cbor(const uint8_t *in, size_t len) {
  bytes_data_t *b = bytes_new(in, len);
  if (!b) return NULL;
  size_t n;
  uint8_t *cbor = bytes_to_cbor(b, &n);
  bytes_free(b);
  g_out_len = n;
  return cbor;
}

EXPORT(kx_psbt_from_cbor) uint8_t *kx_psbt_from_cbor(const uint8_t *in, size_t len) {
  psbt_data_t *p = psbt_from_cbor(in, len);
  if (!p) return NULL;
  size_t n;
  const uint8_t *data = psbt_get_data(p, &n);
  uint8_t *out = dup_bytes(data, n);
  psbt_free(p);
  return out;
}

EXPORT(kx_psbt_to_cbor) uint8_t *kx_psbt_to_cbor(const uint8_t *in, size_t len) {
  psbt_data_t *p = psbt_new(in, len);
  if (!p) return NULL;
  size_t n;
  uint8_t *cbor = psbt_to_cbor(p, &n);
  psbt_free(p);
  g_out_len = n;
  return cbor;
}

/* Words joined by a single space (BIP39 words never contain spaces). */
EXPORT(kx_bip39_words_from_cbor) char *kx_bip39_words_from_cbor(const uint8_t *in, size_t len) {
  bip39_data_t *b = bip39_from_cbor(in, len);
  if (!b) return NULL;
  size_t count;
  char **words = bip39_get_words(b, &count);
  size_t total = 1;
  for (size_t i = 0; i < count; i++) total += strlen(words[i]) + 1;
  char *out = malloc(total);
  if (out) {
    out[0] = 0;
    for (size_t i = 0; i < count; i++) {
      if (i) strcat(out, " ");
      strcat(out, words[i]);
    }
  }
  g_out_len = count;
  bip39_free(b);
  return out;
}

EXPORT(kx_output_from_cbor) char *kx_output_from_cbor(const uint8_t *in, size_t len) {
  output_data_t *o = output_from_cbor(in, len);
  if (!o) return NULL;
  char *d = output_descriptor(o, true);
  output_free(o);
  return d;
}

EXPORT(kx_output_from_cbor_account) char *kx_output_from_cbor_account(const uint8_t *in, size_t len) {
  return output_descriptor_from_cbor_account(in, len);
}

/* ------------------------------------------------------------ constants */

EXPORT(kx_const_int) int kx_const_int(int which) {
  switch (which) {
    case 0: return CRYPTO_PSBT_TAG;
    case 1: return CRYPTO_BIP39_TAG;
    case 2: return CRYPTO_ACCOUNT_TAG;
    case 3: return CRYPTO_OUTPUT_TAG;
    case 10: return UR_DECODER_OK;
    case 11: return UR_DECODER_PROCESSING;
    case 12: return UR_DECODER_NO_RESULT;
    case 13: return UR_DECODER_ERROR_INVALID_SCHEME;
    case 14: return UR_DECODER_ERROR_INVALID_TYPE;
    case 15: return UR_DECODER_ERROR_INVALID_PATH_LENGTH;
    case 16: return UR_DECODER_ERROR_INVALID_SEQUENCE_COMPONENT;
    case 17: return UR_DECODER_ERROR_INVALID_FRAGMENT;
    case 18: return UR_DECODER_ERROR_INVALID_PART;
    case 19: return UR_DECODER_ERROR_INVALID_CHECKSUM;
    case 20: return UR_DECODER_ERROR_MEMORY;
    case 21: return UR_DECODER_ERROR_NULL_POINTER;
  }
  return -9999;
}

EXPORT(kx_const_str) const char *kx_const_str(int which) {
  switch (which) {
    case 0: return PSBT_TYPE.name;
    case 1: return BIP39_TYPE.name;
    case 2: return OUTPUT_TYPE.name;
    case 3: return CRYPTO_ACCOUNT_TYPE_NAME;
  }
  return "";
}
