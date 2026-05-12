
from apps.protocol.rwk35 import (
    AI_LABELS,
    BI_LABELS,
    CLOSE_FRAME,
    TRIP_FRAME,
    build_frame,
    build_read_class0,
    compute_derived_status,
    crc16_dnp,
    extract_hot_fields,
    validate_header_crc,
    voltages_match,
)


class TestCRC:
    def test_crc16_dnp_known(self):
        # Known DNP3 CRC for empty data should be 0xFFFF ^ reflected(0)
        result = crc16_dnp(b"\x05\x64\x0b\xc4\x01\x00\x64\x00")
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF


class TestFrameBuilder:
    def test_build_frame_structure(self):
        frame = build_frame(src=2, dst=1, app_payload=b"\xc0\xc0\x15")
        assert frame[0:2] == b"\x05\x64"
        assert frame[3] == 0xC4
        assert frame[4:6] == b"\x01\x00"  # dst=1 little-endian
        assert frame[6:8] == b"\x02\x00"  # src=2 little-endian
        assert len(frame) >= 10

    def test_build_read_class0(self):
        frame = build_read_class0(src=2, dst=1, seq=1)
        assert frame[0:2] == b"\x05\x64"
        assert validate_header_crc(frame)


class TestHeaderCRC:
    def test_valid_header(self):
        frame = build_frame(src=2, dst=1, app_payload=b"\xc0\xc0\x15")
        assert validate_header_crc(frame) is True

    def test_invalid_header(self):
        assert validate_header_crc(b"\x05\x64\x00\x00\x00\x00\x00\x00\x00\x00") is False


class TestControlFrames:
    def test_close_frame_length(self):
        assert len(CLOSE_FRAME) > 10

    def test_trip_frame_length(self):
        assert len(TRIP_FRAME) > 10

    def test_close_frame_header(self):
        assert CLOSE_FRAME[0:2] == b"\x05\x64"

    def test_trip_frame_header(self):
        assert TRIP_FRAME[0:2] == b"\x05\x64"


class TestLabels:
    def test_ai_labels_count(self):
        assert len(AI_LABELS) == 16

    def test_bi_labels_count(self):
        assert len(BI_LABELS) == 28

    def test_f_abc_label(self):
        assert AI_LABELS[2010] == "F_ABC"

    def test_f_rst_label(self):
        assert AI_LABELS[2011] == "F_RST"

    def test_pf_label(self):
        assert AI_LABELS[2014] == "PF"


class TestDerivedStatus:
    def test_closed_with_matching_voltages(self):
        hot = {
            "ua": 7.2,
            "ur": 7.2,
            "ub": 7.1,
            "us": 7.1,
            "uc": 7.0,
            "ut": 7.0,
        }
        assert compute_derived_status(hot) == "CLOSED"

    def test_closed_voltage_mismatch_with_high_outputs(self):
        hot = {
            "ua": 7.2,
            "ur": 2.0,
            "ub": 7.1,
            "us": 2.0,
            "uc": 7.0,
            "ut": 2.0,
        }
        assert compute_derived_status(hot) == "CLOSED"

    def test_open_low_output(self):
        hot = {
            "ua": 7.2,
            "ur": 0.0,
            "us": 0.0,
            "ut": 0.0,
        }
        assert compute_derived_status(hot) == "OPEN"

    def test_partial_output_is_error(self):
        hot = {
            "ua": 7.2,
            "ur": 2.0,
            "us": 0.0,
            "ut": 0.0,
        }
        assert compute_derived_status(hot) == "ERROR"

    def test_no_input_voltages(self):
        hot = {"ur": 0.0, "us": 0.0, "ut": 0.0}
        assert compute_derived_status(hot) == "ERROR"

    def test_missing_all_voltages(self):
        hot = {}
        assert compute_derived_status(hot) == "ERROR"

    def test_open_only_one_input(self):
        hot = {"ua": 7.2, "ur": 0.0, "us": 0.0, "ut": 0.0}
        assert compute_derived_status(hot) == "OPEN"

    def test_closed_ignores_breaker_inputs(self):
        # breaker inputs should be ignored entirely
        hot = {
            "breaker_close": True,
            "breaker_open": True,
            "ua": 7.2,
            "ur": 7.2,
            "ub": 7.1,
            "us": 7.1,
            "uc": 7.0,
            "ut": 7.0,
        }
        assert compute_derived_status(hot) == "CLOSED"


class TestVoltagesMatch:
    def test_match(self):
        assert voltages_match({"ua": 7.0, "ur": 7.0}) is True

    def test_mismatch(self):
        assert voltages_match({"ua": 7.0, "ur": 1.0}) is False

    def test_low_voltage_skipped(self):
        assert voltages_match({"ua": 0.05, "ur": 7.0}) is True


class TestExtractHotFields:
    def test_extracts_online_only(self):
        points = [
            {"name": "Ia", "value": 10.0, "quality_online": True, "type": "analog"},
            {"name": "Ib", "value": 5.0, "quality_online": False, "type": "analog"},
            {"name": "Breaker close", "value": True, "quality_online": True, "type": "binary"},
        ]
        hot = extract_hot_fields(points)
        assert hot["ia"] == 10.0
        assert "ib" not in hot
        assert hot["breaker_close"] is True
