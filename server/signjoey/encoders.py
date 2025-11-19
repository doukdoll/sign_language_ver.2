# coding: utf-8

import logging
import torch
import torch.nn as nn
from torch import Tensor
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from typing import Tuple

from signjoey.helpers import freeze_params
from signjoey.transformer_layers import (
    PositionalEncoding,
    TransformerEncoderLayer,
)


# pylint: disable=abstract-method
class Encoder(nn.Module):
    """
    기본 인코더 클래스
    """

    @property
    def output_size(self):
        """
        출력 크기를 반환합니다.

        :return:
        """
        return self._output_size


class RecurrentEncoder(Encoder):
    """단어 임베딩 시퀀스를 인코딩합니다"""

    # pylint: disable=unused-argument
    def __init__(
        self,
        rnn_type: str = "gru",
        hidden_size: int = 1,
        emb_size: int = 1,
        num_layers: int = 1,
        dropout: float = 0.0,
        emb_dropout: float = 0.0,
        bidirectional: bool = True,
        freeze: bool = False,
        **kwargs
    ) -> None:
        """
        새로운 순환 인코더를 생성합니다.

        :param rnn_type: RNN 유형: `gru` 또는 `lstm`
        :param hidden_size: 각 RNN의 크기
        :param emb_size: 단어 임베딩의 크기
        :param num_layers: 인코더 RNN 레이어 수
        :param dropout: RNN 레이어 사이에 적용되는 드롭아웃
        :param emb_dropout: RNN 입력(단어 임베딩)에 적용되는 드롭아웃
        :param bidirectional: 양방향 RNN 사용 여부
        :param freeze: 학습 중 인코더의 파라미터 고정 여부
        :param kwargs:
        """

        super(RecurrentEncoder, self).__init__()

        self.emb_dropout = torch.nn.Dropout(p=emb_dropout, inplace=False)
        self.type = rnn_type
        self.emb_size = emb_size

        # RNN 타입 선택 (RNN, LSTM, GRU 지원)
        if rnn_type.lower() == "rnn":
            rnn = nn.RNN
        elif rnn_type.lower() == "lstm":
            rnn = nn.LSTM
        elif rnn_type.lower() == "gru":
            rnn = nn.GRU
        else:
            raise ValueError(f"지원되지 않는 RNN 타입: {rnn_type}. 지원되는 타입: rnn, lstm, gru")

        self.rnn = rnn(
            emb_size,
            hidden_size,
            num_layers,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        self._output_size = 2 * hidden_size if bidirectional else hidden_size

        if freeze:
            freeze_params(self)

    # pylint: disable=invalid-name, unused-argument
    def _check_shapes_input_forward(
        self, embed_src: Tensor, src_length: Tensor, mask: Tensor
    ) -> None:
        """
        `self.forward`에 입력되는 텐서들의 형태가 올바른지 확인합니다.
        `self.forward`와 동일한 입력 의미를 가집니다.

        :param embed_src: 임베딩된 소스 토큰
        :param src_length: 소스 길이
        :param mask: 소스 마스크
        """
        assert embed_src.shape[0] == src_length.shape[0]
        assert embed_src.shape[2] == self.emb_size
        # assert mask.shape == embed_src.shape
        assert len(src_length.shape) == 1

    # pylint: disable=arguments-differ
    def forward(
        self, embed_src: Tensor, src_length: Tensor, mask: Tensor
    ) -> Tuple[Tensor, Tensor]:
        """
        임베딩 시퀀스 x에 양방향 RNN을 적용합니다.
        입력 미니배치 x는 소스 길이에 따라 정렬되어야 합니다.
        x와 mask는 동일한 차원 [batch, time, dim]을 가져야 합니다.

        :param embed_src: 임베딩된 소스 입력,
            형태 (batch_size, src_len, embed_size)
        :param src_length: 소스 입력의 길이
            (패딩 전 토큰 수), 형태 (batch_size)
        :param mask: 패딩 영역을 나타냄 (패딩이 있는 곳은 0),
            형태 (batch_size, src_len, embed_size)
        :return:
            - output: 은닉 상태,
                형태 (batch_size, max_length, directions*hidden)
            - hidden_concat: 마지막 은닉 상태,
                형태 (batch_size, directions*hidden)
        """
        self._check_shapes_input_forward(
            embed_src=embed_src, src_length=src_length, mask=mask
        )

        # RNN 입력에 드롭아웃 적용
        embed_src = self.emb_dropout(embed_src)

        # src_length를 CPU로 이동
        packed = pack_padded_sequence(embed_src, src_length.cpu(), batch_first=True)
        output, hidden = self.rnn(packed)

        # pylint: disable=unused-variable
        if isinstance(hidden, tuple):
            hidden, memory_cell = hidden

        output, _ = pad_packed_sequence(output, batch_first=True)
        # hidden: dir*layers x batch x hidden
        # output: batch x max_length x directions*hidden
        # batch_size = hidden.size()[1] # 이 줄은 새 로직에서 필요 없어짐

        # 수정된 로직 시작
        num_layers = self.rnn.num_layers
        # hidden 텐서는 (num_layers * num_directions, batch_size, hidden_size) 형태입니다.
        
        if self.rnn.bidirectional:
            # 양방향일 경우, 마지막 계층의 정방향 은닉 상태는 인덱스 (2*num_layers - 2)에,
            # 역방향 은닉 상태는 인덱스 (2*num_layers - 1)에 위치합니다.
            # 예: num_layers=1, bi=True -> hidden[0] (fwd), hidden[1] (bwd)
            # 예: num_layers=3, bi=True -> hidden[4] (fwd_layer2), hidden[5] (bwd_layer2)
            last_fwd_h = hidden[2*num_layers - 2, :, :] # 형태: (batch_size, hidden_size)
            last_bwd_h = hidden[2*num_layers - 1, :, :] # 형태: (batch_size, hidden_size)
            # 이들을 연결하여 (batch_size, 2 * hidden_size) 형태의 텐서 생성
            hidden_concat = torch.cat((last_fwd_h, last_bwd_h), dim=1)
        else:
            # 단방향일 경우, 마지막 계층의 은닉 상태는 인덱스 (num_layers - 1)에 위치합니다.
            # 예: num_layers=1, bi=False -> hidden[0]
            # 예: num_layers=3, bi=False -> hidden[2]
            last_fwd_h = hidden[num_layers - 1, :, :] # 형태: (batch_size, hidden_size)
            hidden_concat = last_fwd_h
        # 수정된 로직 끝

        # hidden_concat: batch x directions*hidden (주석은 이전과 동일한 의미)
        return output, hidden_concat

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.rnn)


class FixedLengthRecurrentEncoder(RecurrentEncoder):
    """
    ONNX 호환을 위한 고정 길이 RNN 인코더
    
    pack_padded_sequence를 사용하지 않고 전체 시퀀스를 처리합니다.
    이를 통해 ONNX export가 가능하지만, 패딩된 프레임도 RNN에 입력됩니다.
    
    주의사항:
    - 학습 시 모든 시퀀스를 동일한 길이로 패딩해야 합니다
    - 원본 RecurrentEncoder와 약간 다른 결과를 낼 수 있습니다
    - ONNX export를 위해서는 이 인코더로 재학습이 필요합니다
    """
    
    def __init__(
        self,
        use_packing_in_training: bool = False,
        **kwargs
    ):
        """
        고정 길이 RNN 인코더를 생성합니다.
        
        :param use_packing_in_training: 학습 시에만 packing 사용 여부
                                        True: 학습은 빠르지만 추론과 약간 다름
                                        False: 학습과 추론이 완전히 동일 (권장)
        :param kwargs: RecurrentEncoder의 다른 파라미터들
        """
        super().__init__(**kwargs)
        self.use_packing_in_training = use_packing_in_training
        
        if use_packing_in_training:
            logger = logging.getLogger(__name__)
            logger.info(
                "FixedLengthRecurrentEncoder: 학습 시 packing 사용 활성화됨. "
                "추론 시에는 고정 길이 처리합니다."
            )
    
    def forward(
        self, embed_src: Tensor, src_length: Tensor, mask: Tensor
    ) -> Tuple[Tensor, Tensor]:
        """
        고정 길이 시퀀스를 처리합니다.
        
        :param embed_src: 임베딩된 소스 입력 (batch_size, seq_len, embed_size)
        :param src_length: 소스 길이 (batch_size) - 고정 길이 모드에서는 무시됨
        :param mask: 마스크 (batch_size, 1, seq_len)
        :return: (output, hidden_concat)
        """
        self._check_shapes_input_forward(
            embed_src=embed_src, src_length=src_length, mask=mask
        )
        
        # 드롭아웃 적용
        embed_src = self.emb_dropout(embed_src)
        
        # packing 사용 여부 결정
        use_pack = self.use_packing_in_training and self.training
        
        if use_pack:
            # 학습 시에만 packing 사용 (성능 향상)
            packed = pack_padded_sequence(
                embed_src, src_length.cpu(), batch_first=True, enforce_sorted=False
            )
            output, hidden = self.rnn(packed)
            output, _ = pad_packed_sequence(output, batch_first=True)
        else:
            # 고정 길이 처리 (ONNX 호환)
            output, hidden = self.rnn(embed_src)
        
        # hidden state 추출
        if isinstance(hidden, tuple):
            hidden, _ = hidden  # LSTM의 경우 (hidden, cell)
        
        num_layers = self.rnn.num_layers
        
        if self.rnn.bidirectional:
            # 양방향: 마지막 레이어의 forward/backward 연결
            last_fwd_h = hidden[2*num_layers - 2, :, :]
            last_bwd_h = hidden[2*num_layers - 1, :, :]
            hidden_concat = torch.cat((last_fwd_h, last_bwd_h), dim=1)
        else:
            # 단방향: 마지막 레이어의 hidden state
            hidden_concat = hidden[num_layers - 1, :, :]
        
        return output, hidden_concat
    
    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"rnn={self.rnn}, "
            f"use_packing_in_training={self.use_packing_in_training})"
        )


class MaskedAttentionEncoder(FixedLengthRecurrentEncoder):
    """
    Attention 메커니즘을 사용하는 ONNX 호환 인코더
    
    고정 길이 RNN에 Attention을 추가하여 실제 프레임에만 집중합니다.
    패딩된 프레임의 영향을 최소화하여 더 나은 성능을 제공합니다.
    
    장점:
    - ONNX 완벽 호환
    - 패딩의 영향 최소화
    - 원본 RecurrentEncoder보다 나은 성능 가능
    
    단점:
    - 약간 더 복잡한 구조
    - 재학습 필요
    """
    
    def __init__(
        self,
        attention_dim: int = None,
        **kwargs
    ):
        """
        Attention 기반 인코더를 생성합니다.
        
        :param attention_dim: Attention 차원 (None이면 hidden_size와 동일)
        :param kwargs: FixedLengthRecurrentEncoder의 다른 파라미터들
        """
        # kwargs에 use_packing_in_training이 이미 포함될 수 있으므로 중복 전달 방지
        use_pack = kwargs.pop("use_packing_in_training", False)
        super().__init__(use_packing_in_training=use_pack, **kwargs)
        
        # Attention 레이어
        if attention_dim is None:
            attention_dim = self._output_size
        
        self.attention_dim = attention_dim
        
        # Attention 가중치 계산을 위한 레이어
        self.attention_w = nn.Linear(self._output_size, attention_dim)
        self.attention_v = nn.Linear(attention_dim, 1)
        
        logger = logging.getLogger(__name__)
        logger.info(
            f"MaskedAttentionEncoder 초기화: "
            f"hidden_size={self._output_size}, attention_dim={attention_dim}"
        )
    
    def compute_attention(
        self,
        encoder_outputs: Tensor,
        mask: Tensor
    ) -> Tuple[Tensor, Tensor]:
        """
        Masked attention을 계산합니다.
        
        :param encoder_outputs: RNN 출력 (batch_size, seq_len, hidden_size)
        :param mask: 마스크 (batch_size, 1, seq_len)
        :return: (context_vector, attention_weights)
                 context_vector: (batch_size, hidden_size)
                 attention_weights: (batch_size, seq_len)
        """
        batch_size, seq_len, hidden_size = encoder_outputs.shape
        
        # Attention 스코어 계산
        # (batch_size, seq_len, hidden_size) -> (batch_size, seq_len, attention_dim)
        energy = torch.tanh(self.attention_w(encoder_outputs))
        
        # (batch_size, seq_len, attention_dim) -> (batch_size, seq_len, 1)
        attention_scores = self.attention_v(energy)
        
        # (batch_size, seq_len, 1) -> (batch_size, seq_len)
        attention_scores = attention_scores.squeeze(-1)
        
        # 마스크 적용: 패딩된 위치는 매우 작은 값으로
        # mask: (batch_size, 1, seq_len) -> (batch_size, seq_len)
        mask_squeezed = mask.squeeze(1)
        if mask_squeezed.dtype != torch.bool:
            mask_squeezed = mask_squeezed > 0
        attention_scores = attention_scores.masked_fill(~mask_squeezed, float('-inf'))
        
        # Softmax로 가중치 계산
        attention_weights = torch.softmax(attention_scores, dim=1)
        
        # Weighted sum으로 context vector 생성
        # (batch_size, seq_len) -> (batch_size, seq_len, 1)
        attention_weights_expanded = attention_weights.unsqueeze(-1)
        
        # (batch_size, seq_len, hidden_size) * (batch_size, seq_len, 1)
        # -> (batch_size, seq_len, hidden_size) -> (batch_size, hidden_size)
        context_vector = torch.sum(encoder_outputs * attention_weights_expanded, dim=1)
        
        return context_vector, attention_weights
    
    def forward(
        self, embed_src: Tensor, src_length: Tensor, mask: Tensor
    ) -> Tuple[Tensor, Tensor]:
        """
        Attention 기반 순전파를 수행합니다.
        
        :param embed_src: 임베딩된 소스 입력 (batch_size, seq_len, embed_size)
        :param src_length: 소스 길이 (batch_size)
        :param mask: 마스크 (batch_size, 1, seq_len)
        :return: (output, context_vector)
                 output: RNN 출력 (batch_size, seq_len, hidden_size)
                 context_vector: Attention context (batch_size, hidden_size)
        """
        # 부모 클래스의 forward로 RNN 출력 얻기
        output, _ = super().forward(embed_src, src_length, mask)
        
        # Attention으로 context vector 계산
        context_vector, attention_weights = self.compute_attention(output, mask)
        
        # context_vector를 hidden state 대신 반환
        # 이렇게 하면 실제 프레임에만 집중하는 표현을 얻을 수 있음
        return output, context_vector
    
    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"rnn={self.rnn}, "
            f"attention_dim={self.attention_dim})"
        )


class TransformerEncoder(Encoder):
    """
    N개의 레이어로 구성된 Transformer 인코더
    """

    # pylint: disable=unused-argument
    def __init__(
        self,
        hidden_size: int = 512,
        ff_size: int = 2048,
        num_layers: int = 8,
        num_heads: int = 4,
        dropout: float = 0.1,
        emb_dropout: float = 0.1,
        freeze: bool = False,
        **kwargs
    ):
        """
        새로운 Transformer 인코더를 초기화합니다.
        
        :param hidden_size: 은닉 크기 및 임베딩 크기
        :param ff_size: position-wise feed-forward 레이어의 크기
        :param num_layers: 레이어 수
        :param num_heads: multi-head attention에서의 헤드 수
        :param dropout: 레이어 사이의 드롭아웃 확률
        :param emb_dropout: 임베딩에 적용되는 드롭아웃 확률
        :param freeze: 학습 중 인코더의 파라미터 고정 여부
        """
        super(TransformerEncoder, self).__init__()

        self._output_size = hidden_size

        # num_layers개의 인코더 레이어를 생성하고 리스트에 넣음
        self.layers = nn.ModuleList(
            [
                TransformerEncoderLayer(
                    size=hidden_size,
                    ff_size=ff_size,
                    num_heads=num_heads,
                    dropout=dropout,
                )
                for _ in range(num_layers)
            ]
        )

        self.layer_norm = nn.LayerNorm(hidden_size, eps=1e-6)
        self.pe = PositionalEncoding(hidden_size)
        self.emb_dropout = nn.Dropout(p=emb_dropout)

        if freeze:
            freeze_params(self)

    # pylint: disable=arguments-differ
    def forward(
        self, embed_src: Tensor, src_length: Tensor, mask: Tensor
    ) -> Tuple[Tensor, Tensor]:
        """
        Transformer 인코더를 통과합니다.
        
        :param embed_src: 임베딩된 소스 입력,
            형태 (batch_size, src_len, embed_size)
        :param src_length: 소스 입력의 길이 (사용되지 않음, API 일관성을 위해 존재)
        :param mask: 패딩 영역을 나타냄 (패딩이 있는 곳은 0),
            형태 (batch_size, 1, src_len)
        :return:
            - output: 은닉 상태,
                형태 (batch_size, src_len, hidden_size)
            - hidden_concat: 평균 풀링된 출력,
                형태 (batch_size, hidden_size)
        """
        x = self.pe(embed_src)  # 위치 인코딩 추가
        x = self.emb_dropout(x)

        for layer in self.layers:
            x = layer(x, mask)

        x = self.layer_norm(x)

        # Transformer의 경우, "마지막 은닉 상태"를 평균 풀링으로 근사
        # mask를 사용하여 패딩된 위치를 제외
        # mask: (batch_size, 1, src_len) -> (batch_size, src_len, 1)로 변환
        mask_expanded = mask.transpose(1, 2)  # (batch_size, src_len, 1)
        
        # 마스크를 적용하여 평균 계산
        masked_output = x * mask_expanded  # (batch_size, src_len, hidden_size)
        sum_output = masked_output.sum(dim=1)  # (batch_size, hidden_size)
        seq_lengths = mask_expanded.sum(dim=1)  # (batch_size, 1)
        hidden_concat = sum_output / seq_lengths  # (batch_size, hidden_size)

        return x, hidden_concat

    def __repr__(self):
        return "%s(num_layers=%r, num_heads=%r)" % (
            self.__class__.__name__,
            len(self.layers),
            self.layers[0].src_src_att.num_heads
            if hasattr(self.layers[0], 'src_src_att')
            else 'N/A',
        )