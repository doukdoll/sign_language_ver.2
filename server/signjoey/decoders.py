# coding: utf-8
"""
다양한 디코더 구현
"""
from typing import Optional, Tuple

import torch
import torch.nn as nn
from torch import Tensor
from signjoey.attention import BahdanauAttention, LuongAttention
from signjoey.encoders import Encoder
from signjoey.helpers import freeze_params, subsequent_mask
from signjoey.transformer_layers import PositionalEncoding, TransformerDecoderLayer


# pylint: disable=abstract-method
class Decoder(nn.Module):
    """
    기본 디코더 클래스
    """

    @property
    def output_size(self):
        """
        출력 크기(타겟 어휘 크기)를 반환합니다.

        :return: 출력 크기
        """
        return self._output_size


# pylint: disable=arguments-differ,too-many-arguments
# pylint: disable=too-many-instance-attributes, unused-argument
class RecurrentDecoder(Decoder):
    """Attention이 있는 조건부 RNN 디코더"""

    def __init__(
        self,
        rnn_type: str = "gru",
        emb_size: int = 0,
        hidden_size: int = 0,
        encoder: Encoder = None,
        attention: str = "bahdanau",
        num_layers: int = 1,
        vocab_size: int = 0,
        dropout: float = 0.0,
        emb_dropout: float = 0.0,
        hidden_dropout: float = 0.0,
        init_hidden: str = "bridge",
        input_feeding: bool = True,
        freeze: bool = False,
        **kwargs
    ) -> None:
        """
        Attention이 있는 순환 디코더를 생성합니다.

        :param rnn_type: RNN 유형, 유효한 옵션: "lstm", "gru"
        :param emb_size: 타겟 임베딩 크기
        :param hidden_size: RNN의 크기
        :param encoder: 이 디코더에 연결된 인코더
        :param attention: 어텐션 유형, 유효한 옵션: "bahdanau", "luong"
        :param num_layers: 순환 레이어 수
        :param vocab_size: 타겟 어휘 크기
        :param hidden_dropout: 어텐션 레이어 입력에 적용
        :param dropout: RNN 레이어 사이에 적용
        :param emb_dropout: RNN 입력(단어 임베딩)에 적용
        :param init_hidden: "bridge"(기본값)이면 디코더 은닉 상태가
            마지막 인코더 상태의 투영으로 초기화됨
            "zeros"이면 0으로 초기화
            "last"이면 마지막 인코더 상태와 동일
            (크기가 같은 경우에만)
        :param input_feeding: Luong의 input feeding 사용
        :param freeze: 학습 중 디코더 파라미터 고정
        :param kwargs: 추가 인자
        """

        super(RecurrentDecoder, self).__init__()

        self.emb_dropout = torch.nn.Dropout(p=emb_dropout, inplace=False)
        self.type = rnn_type
        self.hidden_dropout = torch.nn.Dropout(p=hidden_dropout, inplace=False)
        self.hidden_size = hidden_size
        self.emb_size = emb_size

        rnn = nn.GRU if rnn_type == "gru" else nn.LSTM

        self.input_feeding = input_feeding
        if self.input_feeding:  # Luong 스타일
            # 임베딩된 이전 단어 + attention 벡터를 결합한 후 RNN에 공급
            self.rnn_input_size = emb_size + hidden_size
        else:
            # 이전 단어 임베딩만 공급
            self.rnn_input_size = emb_size

        # 디코더 RNN
        self.rnn = rnn(
            self.rnn_input_size,
            hidden_size,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # 출력 레이어 전에 출력과 컨텍스트 벡터를 결합 (Luong 스타일)
        self.att_vector_layer = nn.Linear(
            hidden_size + encoder.output_size, hidden_size, bias=True
        )

        self.output_layer = nn.Linear(hidden_size, vocab_size, bias=False)
        self._output_size = vocab_size

        if attention == "bahdanau":
            self.attention = BahdanauAttention(
                hidden_size=hidden_size,
                key_size=encoder.output_size,
                query_size=hidden_size,
            )
        elif attention == "luong":
            self.attention = LuongAttention(
                hidden_size=hidden_size, key_size=encoder.output_size
            )
        else:
            raise ValueError(
                "알 수 없는 attention 메커니즘: %s. "
                "유효한 옵션: 'bahdanau', 'luong'." % attention
            )

        self.num_layers = num_layers
        self.hidden_size = hidden_size

        # 마지막 레이어의 최종 인코더 상태로부터 초기화
        self.init_hidden_option = init_hidden
        if self.init_hidden_option == "bridge":
            self.bridge_layer = nn.Linear(encoder.output_size, hidden_size, bias=True)
        elif self.init_hidden_option == "last":
            if encoder.output_size != self.hidden_size:
                if encoder.output_size != 2 * self.hidden_size:  # 양방향
                    raise ValueError(
                        "마지막 인코더 상태로 디코더 상태를 초기화하려면 "
                        "크기가 일치해야 합니다 "
                        "(인코더: {} vs. 디코더: {})".format(
                            encoder.output_size, self.hidden_size
                        )
                    )
        if freeze:
            freeze_params(self)

    def _check_shapes_input_forward_step(
        self,
        prev_embed: Tensor,
        prev_att_vector: Tensor,
        encoder_output: Tensor,
        src_mask: Tensor,
        hidden: Tensor,
    ) -> None:
        """
        `self._forward_step`에 입력되는 텐서들의 형태가 올바른지 확인합니다.
        `self._forward_step`와 동일한 입력을 가집니다.

        :param prev_embed: 이전 임베딩
        :param prev_att_vector: 이전 어텐션 벡터
        :param encoder_output: 인코더 출력
        :param src_mask: 소스 마스크
        :param hidden: 은닉 상태
        """
        assert prev_embed.shape[1:] == torch.Size([1, self.emb_size])
        assert prev_att_vector.shape[1:] == torch.Size([1, self.hidden_size])
        assert prev_att_vector.shape[0] == prev_embed.shape[0]
        assert encoder_output.shape[0] == prev_embed.shape[0]
        assert len(encoder_output.shape) == 3
        assert src_mask.shape[0] == prev_embed.shape[0]
        assert src_mask.shape[1] == 1
        assert src_mask.shape[2] == encoder_output.shape[1]
        if isinstance(hidden, tuple):  # LSTM용
            hidden = hidden[0]
        assert hidden.shape[0] == self.num_layers
        assert hidden.shape[1] == prev_embed.shape[0]
        assert hidden.shape[2] == self.hidden_size

    def _check_shapes_input_forward(
        self,
        trg_embed: Tensor,
        encoder_output: Tensor,
        encoder_hidden: Tensor,
        src_mask: Tensor,
        hidden: Tensor = None,
        prev_att_vector: Tensor = None,
    ) -> None:
        """
        `self.forward`에 입력되는 텐서들의 형태가 올바른지 확인합니다.
        `self.forward`와 동일한 입력 의미를 가집니다.

        :param trg_embed: 타겟 임베딩
        :param encoder_output: 인코더 출력
        :param encoder_hidden: 인코더 은닉 상태
        :param src_mask: 소스 마스크
        :param hidden: 은닉 상태
        :param prev_att_vector: 이전 어텐션 벡터
        """
        assert len(encoder_output.shape) == 3
        assert len(encoder_hidden.shape) == 2
        assert encoder_hidden.shape[-1] == encoder_output.shape[-1]
        assert src_mask.shape[1] == 1
        assert src_mask.shape[0] == encoder_output.shape[0]
        assert src_mask.shape[2] == encoder_output.shape[1]
        assert trg_embed.shape[0] == encoder_output.shape[0]
        assert trg_embed.shape[2] == self.emb_size
        if hidden is not None:
            if isinstance(hidden, tuple):  # LSTM용
                hidden = hidden[0]
            assert hidden.shape[1] == encoder_output.shape[0]
            assert hidden.shape[2] == self.hidden_size
        if prev_att_vector is not None:
            assert prev_att_vector.shape[0] == encoder_output.shape[0]
            assert prev_att_vector.shape[2] == self.hidden_size
            assert prev_att_vector.shape[1] == 1

    def _forward_step(
        self,
        prev_embed: Tensor,
        prev_att_vector: Tensor,  # 컨텍스트 또는 att 벡터
        encoder_output: Tensor,
        src_mask: Tensor,
        hidden: Tensor,
    ) -> Tuple[Tensor, Tensor, Tensor]:
        """
        단일 디코더 스텝(1 토큰)을 수행합니다.

        1. `rnn_input`: concat(prev_embed, prev_att_vector [비어있을 수 있음])
        2. `rnn_input`으로 RNN 업데이트
        3. attention 및 context/attention 벡터 계산

        :param prev_embed: 임베딩된 이전 토큰,
            형태 (batch_size, 1, embed_size)
        :param prev_att_vector: 이전 attention 벡터,
            형태 (batch_size, 1, hidden_size)
        :param encoder_output: attention 컨텍스트를 위한 인코더 은닉 상태,
            형태 (batch_size, src_length, encoder.output_size)
        :param src_mask: src 마스크, <eos> 전 영역은 1, 나머지는 0
            형태 (batch_size, 1, src_length)
        :param hidden: 이전 은닉 상태,
            형태 (num_layers, batch_size, hidden_size)
        :return:
            - att_vector: 새로운 attention 벡터 (batch_size, 1, hidden_size),
            - hidden: 새로운 은닉 상태 형태 (batch_size, 1, hidden_size),
            - att_probs: attention 확률 (batch_size, 1, src_len)
        """

        # 형태 확인
        self._check_shapes_input_forward_step(
            prev_embed=prev_embed,
            prev_att_vector=prev_att_vector,
            encoder_output=encoder_output,
            src_mask=src_mask,
            hidden=hidden,
        )

        if self.input_feeding:
            # 입력과 이전 attention 벡터를 연결
            rnn_input = torch.cat([prev_embed, prev_att_vector], dim=2)
        else:
            rnn_input = prev_embed

        rnn_input = self.emb_dropout(rnn_input)

        # rnn_input: batch x 1 x emb+2*enc_size
        _, hidden = self.rnn(rnn_input, hidden)

        # attention 쿼리로 새로운 (최상위) 디코더 레이어 사용
        if isinstance(hidden, tuple):
            query = hidden[0][-1].unsqueeze(1)
        else:
            query = hidden[-1].unsqueeze(1)  # [#layers, B, D] -> [B, 1, D]

        # attention 메커니즘을 사용하여 컨텍스트 벡터 계산
        # attention 메커니즘을 위해 마지막 레이어만 사용
        # 키 투영은 사전 계산됨
        context, att_probs = self.attention(
            query=query, values=encoder_output, mask=src_mask
        )

        # attention 벡터 반환 (Luong)
        # 예측 전에 컨텍스트와 디코더 은닉 상태를 결합
        att_vector_input = torch.cat([query, context], dim=2)
        # batch x 1 x 2*enc_size+hidden_size
        att_vector_input = self.hidden_dropout(att_vector_input)

        att_vector = torch.tanh(self.att_vector_layer(att_vector_input))

        # output: batch x 1 x hidden_size
        return att_vector, hidden, att_probs

    def forward(
        self,
        trg_embed: Tensor,
        encoder_output: Tensor,
        encoder_hidden: Tensor,
        src_mask: Tensor,
        unroll_steps: int,
        hidden: Tensor = None,
        prev_att_vector: Tensor = None,
        **kwargs
    ) -> Tuple[Tensor, Tensor, Tensor, Tensor]:
        """
        `unroll_steps` 스텝만큼 한 번에 한 스텝씩 디코더를 전개합니다.
        매 스텝마다 내부적으로 `_forward_step` 함수가 호출됩니다.

        학습 중에는 타겟 입력(`trg_embed`)이 전체 시퀀스에 대해 이미 알려져 있으므로
        전체 전개가 수행됩니다.
        이 경우 `hidden`과 `prev_att_vector`는 None입니다.

        추론의 경우, 임베딩된 타겟이 이전 타임스텝의 예측이므로
        이 함수는 한 번에 한 스텝씩 호출됩니다.
        이 경우 `hidden`과 `prev_att_vector`는 이 함수의 이전 호출 출력에서 공급됩니다(2번째 스텝부터).

        `src_mask`는 attention을 받지 말아야 하는 인코더 상태의 영역을 마스크하는 데 필요하며,
        첫 번째 <eos> 이후의 모든 것입니다.

        `encoder_output`은 인코더의 은닉 상태이며
        attention의 컨텍스트로 사용됩니다.

        `encoder_hidden`은 첫 번째 은닉 디코더 상태를 초기화하는 데 사용되는
        마지막 인코더 은닉 상태입니다
        (`self.init_hidden_option`이 "bridge" 또는 "last"인 경우).

        :param trg_embed: 임베딩된 타겟 입력,
            형태 (batch_size, trg_length, embed_size)
        :param encoder_output: 인코더의 은닉 상태,
            형태 (batch_size, src_length, encoder.output_size)
        :param encoder_hidden: 인코더의 마지막 상태,
            형태 (batch_size x encoder.output_size)
        :param src_mask: src 상태에 대한 마스크: 패딩 영역은 0,
            나머지는 1, 형태 (batch_size, 1, src_length)
        :param unroll_steps: 디코더 RNN을 전개할 스텝 수
        :param hidden: 이전 디코더 은닉 상태,
            주어지지 않으면 `self.init_hidden`에서 초기화됨,
            형태 (num_layers, batch_size, hidden_size)
        :param prev_att_vector: 이전 attentional 벡터,
            주어지지 않으면 0으로 초기화됨,
            형태 (batch_size, 1, hidden_size)
        :return:
            - outputs: 형태 (batch_size, unroll_steps, vocab_size),
            - hidden: 마지막 은닉 상태 (num_layers, batch_size, hidden_size),
            - att_probs: attention 확률
                형태 (batch_size, unroll_steps, src_length),
            - att_vectors: attentional 벡터
                형태 (batch_size, unroll_steps, hidden_size)
        """

        # 형태 확인
        self._check_shapes_input_forward(
            trg_embed=trg_embed,
            encoder_output=encoder_output,
            encoder_hidden=encoder_hidden,
            src_mask=src_mask,
            hidden=hidden,
            prev_att_vector=prev_att_vector,
        )

        # 최종 인코더 은닉 상태로부터 디코더 은닉 상태 초기화
        if hidden is None:
            hidden = self._init_hidden(encoder_hidden)

        # 투영된 인코더 출력을 사전 계산
        # (attention 메커니즘을 위한 "키")
        # 이것은 효율성을 위해서만 수행됩니다
        if hasattr(self.attention, "compute_proj_keys"):
            self.attention.compute_proj_keys(keys=encoder_output)

        # 여기에 모든 중간 attention 벡터를 저장 (예측에 사용)
        att_vectors = []
        att_probs = []

        batch_size = encoder_output.size(0)

        if prev_att_vector is None:
            with torch.no_grad():
                prev_att_vector = encoder_output.new_zeros(
                    [batch_size, 1, self.hidden_size]
                )

        # `unroll_steps` 스텝만큼 디코더 RNN 전개
        for i in range(unroll_steps):
            prev_embed = trg_embed[:, i].unsqueeze(1)  # batch, 1, emb
            prev_att_vector, hidden, att_prob = self._forward_step(
                prev_embed=prev_embed,
                prev_att_vector=prev_att_vector,
                encoder_output=encoder_output,
                src_mask=src_mask,
                hidden=hidden,
            )
            att_vectors.append(prev_att_vector)
            att_probs.append(att_prob)

        att_vectors = torch.cat(att_vectors, dim=1)
        # att_vectors: batch, unroll_steps, hidden_size
        att_probs = torch.cat(att_probs, dim=1)
        # att_probs: batch, unroll_steps, src_length
        outputs = self.output_layer(att_vectors)
        # outputs: batch, unroll_steps, vocab_size
        return outputs, hidden, att_probs, att_vectors

    def _init_hidden(self, encoder_final: Tensor = None) -> Tuple[Tensor, Optional[Tensor]]:
        """
        마지막 인코더 레이어의 최종 인코더 상태에 조건을 부여한
        초기 디코더 상태를 반환합니다.

        `self.init_hidden_option == "bridge"`이고
        `encoder_final`이 주어진 경우, 이것은 인코더 상태의 투영입니다.

        `self.init_hidden_option == "last"`이고
        크기가 일치하는 `encoder_final`의 경우, 이것은 인코더 상태로 설정됩니다.
        인코더가 디코더 상태의 두 배인 경우 (예: 양방향인 경우),
        정방향 은닉 상태만 사용합니다.

        `self.init_hidden_option == "zero"`인 경우, 0으로 초기화됩니다.

        LSTM의 경우 은닉 상태와 메모리 셀을 모두 초기화합니다
        인코더 은닉 상태의 동일한 투영/복사로.

        모든 디코더 레이어는 동일한 초기 값으로 초기화됩니다.

        :param encoder_final: 인코더의 마지막 레이어의 최종 상태,
            형태 (batch_size, encoder_hidden_size)
        :return: GRU이면 은닉 상태, LSTM이면 (은닉 상태, 메모리 셀),
            형태 (batch_size, hidden_size)
        """
        batch_size = encoder_final.size(0)

        # 여러 레이어의 경우: 모든 레이어에 대해 동일
        if self.init_hidden_option == "bridge" and encoder_final is not None:
            # num_layers x batch_size x hidden_size
            hidden = (
                torch.tanh(self.bridge_layer(encoder_final))
                .unsqueeze(0)
                .repeat(self.num_layers, 1, 1)
            )
        elif self.init_hidden_option == "last" and encoder_final is not None:
            # 특수 케이스: 인코더가 양방향: 정방향 상태만 사용
            if encoder_final.shape[1] == 2 * self.hidden_size:  # 양방향
                encoder_final = encoder_final[:, : self.hidden_size]
            hidden = encoder_final.unsqueeze(0).repeat(self.num_layers, 1, 1)
        else:  # 0으로 초기화
            with torch.no_grad():
                hidden = encoder_final.new_zeros(
                    self.num_layers, batch_size, self.hidden_size
                )

        return (hidden, hidden) if isinstance(self.rnn, nn.LSTM) else hidden

    def __repr__(self):
        return "RecurrentDecoder(rnn=%r, attention=%r)" % (self.rnn, self.attention)


# pylint: disable=arguments-differ,too-many-arguments
# pylint: disable=too-many-instance-attributes, unused-argument
class TransformerDecoder(Decoder):
    """
    N개의 마스크된 레이어가 있는 Transformer 디코더.
    디코더 레이어는 attention 헤드가 미래를 볼 수 없도록 마스크됩니다.
    """

    def __init__(
        self,
        num_layers: int = 4,
        num_heads: int = 8,
        hidden_size: int = 512,
        ff_size: int = 2048,
        dropout: float = 0.1,
        emb_dropout: float = 0.1,
        vocab_size: int = 1,
        freeze: bool = False,
        **kwargs
    ):
        """
        Transformer 디코더를 초기화합니다.

        :param num_layers: Transformer 레이어 수
        :param num_heads: 각 레이어의 헤드 수
        :param hidden_size: 은닉 크기
        :param ff_size: position-wise feed-forward 크기
        :param dropout: 드롭아웃 확률 (1-keep)
        :param emb_dropout: 임베딩에 대한 드롭아웃 확률
        :param vocab_size: 출력 어휘 크기
        :param freeze: True로 설정하면 모든 디코더 파라미터 고정
        :param kwargs: 추가 인자
        """
        super(TransformerDecoder, self).__init__()

        self._hidden_size = hidden_size
        self._output_size = vocab_size

        # num_layers개의 디코더 레이어를 생성하고 리스트에 넣음
        self.layers = nn.ModuleList(
            [
                TransformerDecoderLayer(
                    size=hidden_size,
                    ff_size=ff_size,
                    num_heads=num_heads,
                    dropout=dropout,
                )
                for _ in range(num_layers)
            ]
        )

        self.pe = PositionalEncoding(hidden_size)
        self.layer_norm = nn.LayerNorm(hidden_size, eps=1e-6)

        self.emb_dropout = nn.Dropout(p=emb_dropout)
        self.output_layer = nn.Linear(hidden_size, vocab_size, bias=False)

        if freeze:
            freeze_params(self)

    def forward(
        self,
        trg_embed: Tensor = None,
        encoder_output: Tensor = None,
        encoder_hidden: Tensor = None,
        src_mask: Tensor = None,
        unroll_steps: int = None,
        hidden: Tensor = None,
        trg_mask: Tensor = None,
        **kwargs
    ) -> Tuple[Tensor, Tensor, None, None]:
        """
        Transformer 디코더 순전파.

        :param trg_embed: 임베딩된 타겟
        :param encoder_output: 소스 표현
        :param encoder_hidden: 사용하지 않음
        :param src_mask: 소스 마스크
        :param unroll_steps: 사용하지 않음
        :param hidden: 사용하지 않음
        :param trg_mask: 타겟 패딩을 마스크하기 위해 사용
                         여기서 subsequent 마스크가 적용됨
        :param kwargs: 추가 인자
        :return: (출력, 은닉, None, None)
        """
        assert trg_mask is not None, "Transformer에는 trg_mask가 필요합니다"

        x = self.pe(trg_embed)  # 단어 임베딩에 위치 인코딩 추가
        x = self.emb_dropout(x)

        trg_mask = trg_mask & subsequent_mask(trg_embed.size(1)).type_as(trg_mask)

        for layer in self.layers:
            x = layer(x=x, memory=encoder_output, src_mask=src_mask, trg_mask=trg_mask)

        x = self.layer_norm(x)
        output = self.output_layer(x)

        return output, x, None, None

    def __repr__(self):
        return "%s(num_layers=%r, num_heads=%r)" % (
            self.__class__.__name__,
            len(self.layers),
            self.layers[0].trg_trg_att.num_heads,
        )
