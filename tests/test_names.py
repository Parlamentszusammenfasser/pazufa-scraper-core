"""Tests for name normalization."""

from pazufa_corelib.normalization.names import normalize_name, normalize_name_key

# ---------------------------------------------------------------------------
# normalize_name_key
# ---------------------------------------------------------------------------


class TestNormalizeNameKey:
    def test_nfkc_ligature(self) -> None:
        assert normalize_name_key("ﬁscher") == "fischer"

    def test_umlaut_fold_u(self) -> None:
        assert normalize_name_key("Müller") == "mueller"

    def test_umlaut_fold_o(self) -> None:
        assert normalize_name_key("Möller") == "moeller"

    def test_umlaut_fold_a(self) -> None:
        assert normalize_name_key("Bäcker") == "baecker"

    def test_umlaut_fold_sz(self) -> None:
        assert normalize_name_key("Straße") == "strasse"

    def test_lowercase(self) -> None:
        assert normalize_name_key("MUELLER") == "mueller"

    def test_punctuation_stripped(self) -> None:
        assert normalize_name_key("Müller, Maria") == "mueller maria"

    def test_hyphen_stripped(self) -> None:
        assert normalize_name_key("Müller-Franken") == "muellerfranken"

    def test_whitespace_collapsed(self) -> None:
        assert normalize_name_key("  Maria   Müller  ") == "maria mueller"

    def test_invisible_chars_stripped(self) -> None:
        assert normalize_name_key("Mül​ler") == "mueller"

    def test_empty_string(self) -> None:
        assert normalize_name_key("") == ""

    def test_mueller_variants_equal(self) -> None:
        assert normalize_name_key("Müller") == normalize_name_key("Mueller")

    def test_idempotent(self) -> None:
        key = normalize_name_key("Dr. María Ångström")
        assert normalize_name_key(key) == key


# ---------------------------------------------------------------------------
# normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_token_sort_firstname_lastname(self) -> None:
        assert normalize_name("Maria Müller") == normalize_name("Müller Maria")

    def test_token_sort_comma_form(self) -> None:
        assert normalize_name("Müller, Maria") == normalize_name("Maria Müller")

    def test_honorific_dr_stripped(self) -> None:
        assert normalize_name("Dr. Maria Müller") == normalize_name("Maria Müller")

    def test_honorific_prof_stripped(self) -> None:
        assert normalize_name("Prof. Schmidt") == normalize_name("Schmidt")

    def test_honorific_prof_dr_stripped(self) -> None:
        assert normalize_name("Prof. Dr. Schmidt") == normalize_name("Schmidt")

    def test_honorific_mdb_stripped(self) -> None:
        assert normalize_name("Maria Müller MdB") == normalize_name("Maria Müller")

    def test_honorific_mdl_stripped(self) -> None:
        assert normalize_name("Hans Maier MdL") == normalize_name("Hans Maier")

    def test_honorific_dipl_stripped(self) -> None:
        assert normalize_name("Dipl.-Ing. Bernd Weber") == normalize_name("Bernd Weber")

    def test_umlaut_fold_applied(self) -> None:
        assert normalize_name("Müller") == normalize_name("Mueller")

    def test_combined_honorific_umlaut_sort(self) -> None:
        assert normalize_name("Dr. Maria Müller MdB") == normalize_name("mueller maria")

    def test_empty_string(self) -> None:
        assert normalize_name("") == ""

    def test_whitespace_only(self) -> None:
        assert normalize_name("   ") == ""

    def test_integration_same_key_from_different_forms(self) -> None:
        variants = [
            "Dr. Maria Müller",
            "Müller, Maria",
            "Mueller, Maria",
            "Maria Mueller",
            "Dr. Müller, Maria MdL",
        ]
        keys = [normalize_name(v) for v in variants]
        assert len(set(keys)) == 1, f"Expected one unique key, got: {set(keys)}"
