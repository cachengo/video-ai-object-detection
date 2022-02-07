# Copyright © 2020 Arm Ltd and Contributors. All rights reserved.
# SPDX-License-Identifier: MIT

"""Class used to extract the Mel-frequency cepstral coefficients from a given audio frame."""

import numpy as np


class MFCCParams:
    def __init__(self, sampling_freq, num_fbank_bins,
                 mel_lo_freq, mel_hi_freq, num_mfcc_feats, frame_len, use_htk_method, n_FFT):
        self.sampling_freq = sampling_freq
        self.num_fbank_bins = num_fbank_bins
        self.mel_lo_freq = mel_lo_freq
        self.mel_hi_freq = mel_hi_freq
        self.num_mfcc_feats = num_mfcc_feats
        self.frame_len = frame_len
        self.use_htk_method = use_htk_method
        self.n_FFT = n_FFT


class MFCC:

    def __init__(self, mfcc_params):
        self.mfcc_params = mfcc_params
        self.FREQ_STEP = 200.0 / 3
        self.MIN_LOG_HZ = 1000.0
        self.MIN_LOG_MEL = self.MIN_LOG_HZ / self.FREQ_STEP
        self.LOG_STEP = 1.8562979903656 / 27.0
        self.__frame_len_padded = int(2 ** (np.ceil((np.log(self.mfcc_params.frame_len) / np.log(2.0)))))
        self.__filter_bank_initialised = False
        self.__frame = np.zeros(self.__frame_len_padded)
        self.__buffer = np.zeros(self.__frame_len_padded)
        self.__filter_bank_filter_first = np.zeros(self.mfcc_params.num_fbank_bins)
        self.__filter_bank_filter_last = np.zeros(self.mfcc_params.num_fbank_bins)
        self.__mel_energies = np.zeros(self.mfcc_params.num_fbank_bins)
        self.__dct_matrix = self.create_dct_matrix(self.mfcc_params.num_fbank_bins, self.mfcc_params.num_mfcc_feats)
        self.__mel_filter_bank = self.create_mel_filter_bank()
        self.__np_mel_bank = np.zeros([self.mfcc_params.num_fbank_bins, int(self.mfcc_params.n_FFT / 2) + 1])

        for i in range(self.mfcc_params.num_fbank_bins):
            k = 0
            for j in range(int(self.__filter_bank_filter_first[i]), int(self.__filter_bank_filter_last[i]) + 1):
                self.__np_mel_bank[i, j] = self.__mel_filter_bank[i][k]
                k += 1

    def mel_scale(self, freq, use_htk_method):
        """
        Gets the mel scale for a particular sample frequency.

        Args:
            freq: The sampling frequency.
            use_htk_method: Boolean to set whether to use HTK method or not.

        Returns:
            the mel scale
        """
        if use_htk_method:
            return 1127.0 * np.log(1.0 + freq / 700.0)
        else:
            mel = freq / self.FREQ_STEP

        if freq >= self.MIN_LOG_HZ:
            mel = self.MIN_LOG_MEL + np.log(freq / self.MIN_LOG_HZ) / self.LOG_STEP
        return mel

    def inv_mel_scale(self, mel_freq, use_htk_method):
        """
        Gets the sample frequency for a particular mel.

        Args:
            mel_freq: The mel frequency.
            use_htk_method: Boolean to set whether to use HTK method or not.

        Returns:
            the sample frequency
        """
        if use_htk_method:
            return 700.0 * (np.exp(mel_freq / 1127.0) - 1.0)
        else:
            freq = self.FREQ_STEP * mel_freq

            if mel_freq >= self.MIN_LOG_MEL:
                freq = self.MIN_LOG_HZ * np.exp(self.LOG_STEP * (mel_freq - self.MIN_LOG_MEL))
            return freq

    def mfcc_compute(self, audio_data):
        """
        Extracts the MFCC for a single frame.

        Args:
            audio_data: The audio data to process.

        Returns:
            the MFCC features
        """
        if len(audio_data) != self.mfcc_params.frame_len:
            raise ValueError(
                f"audio_data buffer size {len(audio_data)} does not match the frame length {self.mfcc_params.frame_len}")

        audio_data = np.array(audio_data)
        spec = np.abs(np.fft.rfft(np.hanning(self.mfcc_params.n_FFT + 1)[0:self.mfcc_params.n_FFT] * audio_data,
                                  self.mfcc_params.n_FFT)) ** 2
        mel_energy = np.dot(self.__np_mel_bank.astype(np.float32),
                            np.transpose(spec).astype(np.float32))

        mel_energy += 1e-10
        log_mel_energy = 10.0 * np.log10(mel_energy)
        top_db = 80.0

        log_mel_energy = np.maximum(log_mel_energy, log_mel_energy.max() - top_db)

        mfcc_feats = np.dot(self.__dct_matrix, log_mel_energy)

        return mfcc_feats

    def create_dct_matrix(self, num_fbank_bins, num_mfcc_feats):
        """
        Creates the Discrete Cosine Transform matrix to be used in the compute function.

        Args:
            num_fbank_bins: The number of filter bank bins
            num_mfcc_feats: the number of MFCC features

        Returns:
            the DCT matrix
        """
        dct_m = np.zeros(num_fbank_bins * num_mfcc_feats)
        for k in range(num_mfcc_feats):
            for n in range(num_fbank_bins):
                if k == 0:
                    dct_m[(k * num_fbank_bins) + n] = 2 * np.sqrt(1 / (4 * num_fbank_bins)) * np.cos(
                        (np.pi / num_fbank_bins) * (n + 0.5) * k)
                else:
                    dct_m[(k * num_fbank_bins) + n] = 2 * np.sqrt(1 / (2 * num_fbank_bins)) * np.cos(
                        (np.pi / num_fbank_bins) * (n + 0.5) * k)

        dct_m = np.reshape(dct_m, [self.mfcc_params.num_mfcc_feats, self.mfcc_params.num_fbank_bins])
        return dct_m

    def create_mel_filter_bank(self):
        """
        Creates the Mel filter bank.

        Returns:
            the mel filter bank
        """
        num_fft_bins = int(self.__frame_len_padded / 2)
        fft_bin_width = self.mfcc_params.sampling_freq / self.__frame_len_padded

        mel_low_freq = self.mel_scale(self.mfcc_params.mel_lo_freq, False)
        mel_high_freq = self.mel_scale(self.mfcc_params.mel_hi_freq, False)
        mel_freq_delta = (mel_high_freq - mel_low_freq) / (self.mfcc_params.num_fbank_bins + 1)

        this_bin = np.zeros(num_fft_bins)
        mel_fbank = [0] * self.mfcc_params.num_fbank_bins

        for bin_num in range(self.mfcc_params.num_fbank_bins):
            left_mel = mel_low_freq + bin_num * mel_freq_delta
            center_mel = mel_low_freq + (bin_num + 1) * mel_freq_delta
            right_mel = mel_low_freq + (bin_num + 2) * mel_freq_delta
            first_index = last_index = -1

            for i in range(num_fft_bins):
                freq = (fft_bin_width * i)
                mel = self.mel_scale(freq, False)
                this_bin[i] = 0.0

                if (mel > left_mel) and (mel < right_mel):
                    if mel <= center_mel:
                        weight = (mel - left_mel) / (center_mel - left_mel)
                    else:
                        weight = (right_mel - mel) / (right_mel - center_mel)

                    enorm = 2.0 / (self.inv_mel_scale(right_mel, False) - self.inv_mel_scale(left_mel, False))
                    weight *= enorm
                    this_bin[i] = weight

                    if first_index == -1:
                        first_index = i
                    last_index = i

            self.__filter_bank_filter_first[bin_num] = first_index
            self.__filter_bank_filter_last[bin_num] = last_index
            mel_fbank[bin_num] = np.zeros(last_index - first_index + 1)
            j = 0

            for i in range(first_index, last_index + 1):
                mel_fbank[bin_num][j] = this_bin[i]
                j += 1

        return mel_fbank


class Preprocessor:

    def __init__(self, mfcc, model_input_size, stride):
        self.model_input_size = model_input_size
        self.stride = stride

        # Savitzky - Golay differential filters
        self.__savgol_order1_coeffs = np.array([6.66666667e-02, 5.00000000e-02, 3.33333333e-02,
                                                1.66666667e-02, -3.46944695e-18, -1.66666667e-02,
                                                -3.33333333e-02, -5.00000000e-02, -6.66666667e-02])

        self.savgol_order2_coeffs = np.array([0.06060606, 0.01515152, -0.01731602,
                                              -0.03679654, -0.04329004, -0.03679654,
                                              -0.01731602, 0.01515152, 0.06060606])

        self.__mfcc_calc = mfcc

    def __normalize(self, values):
        """
        Normalize values to mean 0 and std 1
        """
        ret_val = (values - np.mean(values)) / np.std(values)
        return ret_val

    def __get_features(self, features, mfcc_instance, audio_data):
        idx = 0
        while len(features) < self.model_input_size * mfcc_instance.mfcc_params.num_mfcc_feats:
            features.extend(mfcc_instance.mfcc_compute(audio_data[idx:idx + int(mfcc_instance.mfcc_params.frame_len)]))
            idx += self.stride

    def extract_features(self, audio_data):
        """
        Extracts the MFCC features, and calculates each features first and second order derivative.
        The matrix returned should be sized appropriately for input to the model, based
        on the model info specified in the MFCC instance.

        Args:
            mfcc_instance: The instance of MFCC used for this calculation
            audio_data: the audio data to be used for this calculation
        Returns:
            the derived MFCC feature vector, sized appropriately for inference
        """

        num_samples_per_inference = ((self.model_input_size - 1)
                                     * self.stride) + self.__mfcc_calc.mfcc_params.frame_len
        if len(audio_data) < num_samples_per_inference:
            raise ValueError("audio_data size for feature extraction is smaller than "
                             "the expected number of samples needed for inference")

        features = []
        self.__get_features(features, self.__mfcc_calc, np.asarray(audio_data))
        features = np.reshape(np.array(features), (self.model_input_size, self.__mfcc_calc.mfcc_params.num_mfcc_feats))

        mfcc_delta_np = np.zeros_like(features)
        mfcc_delta2_np = np.zeros_like(features)

        for i in range(features.shape[1]):
            idelta = np.convolve(features[:, i], self.__savgol_order1_coeffs, 'same')
            mfcc_delta_np[:, i] = (idelta)
            ideltadelta = np.convolve(features[:, i], self.savgol_order2_coeffs, 'same')
            mfcc_delta2_np[:, i] = (ideltadelta)

        features = np.concatenate((self.__normalize(features), self.__normalize(mfcc_delta_np),
                                   self.__normalize(mfcc_delta2_np)), axis=1)

        return np.float32(features)
