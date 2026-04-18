import numpy as np
from audio_client.cli import parse_args, resample, to_pcm16


class TestParseArgs:
    """Tests for CLI argument parsing."""

    def test_default_args(self):
        args = parse_args(["--sala", "test"])
        assert args.sala == "test"
        assert args.server == "ws://localhost:8000"
        assert args.lang == "it-IT"
        assert args.device is None

    def test_custom_args(self):
        args = parse_args([
            "--sala", "auditorium",
            "--server", "ws://remote:9000",
            "--lang", "en-US",
            "--device", "3",
        ])
        assert args.sala == "auditorium"
        assert args.server == "ws://remote:9000"
        assert args.lang == "en-US"
        assert args.device == 3

    def test_list_devices_flag(self):
        args = parse_args(["--list-devices"])
        assert args.list_devices is True


class TestAudioConversion:
    """Tests for audio format conversion."""

    def test_float32_to_pcm16(self):
        audio = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
        pcm = to_pcm16(audio)
        assert isinstance(pcm, bytes)
        assert len(pcm) == 10

    def test_resample_to_16khz(self):
        audio_44100 = np.zeros(44100, dtype=np.float32)
        resampled = resample(audio_44100, 44100, 16000)
        assert len(resampled) == 16000

    def test_resample_same_rate(self):
        audio = np.zeros(16000, dtype=np.float32)
        resampled = resample(audio, 16000, 16000)
        assert len(resampled) == 16000
