# -*- coding: utf-8 -*-
"""
Transformer 레이어 모듈
"""

import math
import torch
import torch.nn as nn
from torch import Tensor


# pylint: disable=arguments-differ
class MultiHeadedAttention(nn.Module):
    """
    "Attention is All You Need"의 Multi-Head Attention 모듈

    OpenNMT-py 구현을 수정했습니다.
    https://github.com/OpenNMT/OpenNMT-py
    """

    def __init__(self, num_heads: int, size: int, dropout: float = 0.1):
        """
        멀티헤드 어텐션 레이어를 생성합니다.
        
        :param num_heads: 헤드 수
        :param size: 모델 크기 (num_heads로 나누어 떨어져야 함)
        :param dropout: 드롭아웃 확률
        """
        super(MultiHeadedAttention, self).__init__()

        assert size % num_heads == 0

        self.head_size = head_size = size // num_heads
        self.model_size = size
        self.num_heads = num_heads

        self.k_layer = nn.Linear(size, num_heads * head_size)
        self.v_layer = nn.Linear(size, num_heads * head_size)
        self.q_layer = nn.Linear(size, num_heads * head_size)

        self.output_layer = nn.Linear(size, size)
        self.softmax = nn.Softmax(dim=-1)
        self.dropout = nn.Dropout(dropout)

    def forward(self, k: Tensor, v: Tensor, q: Tensor, mask: Tensor = None):
        """
        멀티헤드 어텐션을 계산합니다.

        :param k: 키   [B, M, D] (M은 시퀀스 길이)
        :param v: 값   [B, M, D]
        :param q: 쿼리 [B, M, D]
        :param mask: 선택적 마스크 [B, 1, M]
        :return: 어텐션 출력
        """
        batch_size = k.size(0)
        num_heads = self.num_heads

        # 쿼리(q), 키(k), 값(v)를 투영
        k = self.k_layer(k)
        v = self.v_layer(v)
        q = self.q_layer(q)

        # 계산을 위해 q, k, v를 [batch_size, num_heads, ...]로 재구성
        k = k.view(batch_size, -1, num_heads, self.head_size).transpose(1, 2)
        v = v.view(batch_size, -1, num_heads, self.head_size).transpose(1, 2)
        q = q.view(batch_size, -1, num_heads, self.head_size).transpose(1, 2)

        # 점수 계산
        q = q / math.sqrt(self.head_size)

        # batch x num_heads x query_len x key_len
        scores = torch.matmul(q, k.transpose(2, 3))

        # 마스크 적용 (있는 경우)
        # 헤드를 위한 차원 추가: [B, 1, 1, M]
        if mask is not None:
            scores = scores.masked_fill(~mask.unsqueeze(1), float("-inf"))

        # 어텐션 드롭아웃 적용 및 컨텍스트 벡터 계산
        attention = self.softmax(scores)
        attention = self.dropout(attention)

        # 컨텍스트 벡터 획득 (어텐션으로 값 선택) 및 재구성
        # [B, M, D]로 되돌림
        context = torch.matmul(attention, v)
        context = (
            context.transpose(1, 2)
            .contiguous()
            .view(batch_size, -1, num_heads * self.head_size)
        )

        output = self.output_layer(context)

        return output


# pylint: disable=arguments-differ
class PositionwiseFeedForward(nn.Module):
    """
    Position-wise Feed-forward 레이어
    ff_size로 투영한 다음 input_size로 되돌립니다.
    """

    def __init__(self, input_size, ff_size, dropout=0.1):
        """
        Position-wise feed-forward 레이어를 초기화합니다.
        
        :param input_size: 입력의 차원
        :param ff_size: 중간 표현의 차원
        :param dropout: 드롭아웃 확률
        """
        super(PositionwiseFeedForward, self).__init__()
        self.layer_norm = nn.LayerNorm(input_size, eps=1e-6)
        self.pwff_layer = nn.Sequential(
            nn.Linear(input_size, ff_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(ff_size, input_size),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        x_norm = self.layer_norm(x)
        return self.pwff_layer(x_norm) + x


# pylint: disable=arguments-differ
class PositionalEncoding(nn.Module):
    """
    위치 인코딩(PE)을 사전 계산합니다.
    순전파 시, 필요한 만큼의 타임스텝에 대해 입력에 위치 인코딩을 추가합니다.

    OpenNMT-py 구현 기반
    https://github.com/OpenNMT/OpenNMT-py
    """

    def __init__(self, size: int = 0, max_len: int = 5000):
        """
        최대 길이 max_len의 위치 인코딩
        
        :param size: 임베딩 차원
        :param max_len: 최대 시퀀스 길이
        """
        if size % 2 != 0:
            raise ValueError(
                "sin/cos 위치 인코딩을 홀수 차원에 사용할 수 없습니다 "
                "(dim={:d})".format(size)
            )
        pe = torch.zeros(max_len, size)
        position = torch.arange(0, max_len).unsqueeze(1)
        div_term = torch.exp(
            (torch.arange(0, size, 2, dtype=torch.float) * -(math.log(10000.0) / size))
        )
        pe[:, 0::2] = torch.sin(position.float() * div_term)
        pe[:, 1::2] = torch.cos(position.float() * div_term)
        pe = pe.unsqueeze(0)  # shape: [1, size, max_len]
        super(PositionalEncoding, self).__init__()
        self.register_buffer("pe", pe)
        self.dim = size

    def forward(self, emb):
        """
        임베딩에 위치 인코딩 추가
        
        :param emb: 입력 임베딩 텐서 [B, T, D]
        :return: 위치 인코딩이 추가된 텐서
        """
        return emb + self.pe[:, : emb.size(1)]


class TransformerEncoderLayer(nn.Module):
    """
    단일 Transformer 인코더 레이어
    멀티헤드 셀프 어텐션과 position-wise feed-forward로 구성
    """

    def __init__(
        self,
        size: int = 0,
        ff_size: int = 0,
        num_heads: int = 0,
        dropout: float = 0.1,
    ):
        """
        Transformer 인코더 레이어를 초기화합니다.
        
        :param size: 모델 차원
        :param ff_size: feed-forward 네트워크의 차원
        :param num_heads: 어텐션 헤드 수
        :param dropout: 드롭아웃 확률
        """
        super(TransformerEncoderLayer, self).__init__()

        self.layer_norm = nn.LayerNorm(size, eps=1e-6)
        self.src_src_att = MultiHeadedAttention(num_heads, size, dropout=dropout)
        self.feed_forward = PositionwiseFeedForward(
            input_size=size, ff_size=ff_size, dropout=dropout
        )
        self.dropout = nn.Dropout(dropout)
        self.size = size

    # pylint: disable=arguments-differ
    def forward(self, x: Tensor, mask: Tensor) -> Tensor:
        """
        순전파를 수행합니다.
        
        :param x: 입력 텐서 [B, T, D]
        :param mask: 마스크 텐서 [B, 1, T]
        :return: 출력 텐서 [B, T, D]
        """
        x_norm = self.layer_norm(x)
        h = self.src_src_att(x_norm, x_norm, x_norm, mask)
        h = self.dropout(h) + x
        o = self.feed_forward(h)
        return o


class TransformerDecoderLayer(nn.Module):
    """
    단일 Transformer 디코더 레이어
    셀프 어텐션, 소스 어텐션, position-wise feed-forward로 구성
    """

    def __init__(
        self, size: int = 0, ff_size: int = 0, num_heads: int = 0, dropout: float = 0.1
    ):
        """
        Transformer 디코더 레이어를 초기화합니다.
        
        :param size: 모델 차원
        :param ff_size: feed-forward 네트워크의 차원
        :param num_heads: 어텐션 헤드 수
        :param dropout: 드롭아웃 확률
        """
        super(TransformerDecoderLayer, self).__init__()
        self.size = size

        self.trg_trg_att = MultiHeadedAttention(num_heads, size, dropout=dropout)
        self.src_trg_att = MultiHeadedAttention(num_heads, size, dropout=dropout)

        self.feed_forward = PositionwiseFeedForward(
            input_size=size, ff_size=ff_size, dropout=dropout
        )

        self.x_layer_norm = nn.LayerNorm(size, eps=1e-6)
        self.dec_layer_norm = nn.LayerNorm(size, eps=1e-6)

        self.dropout = nn.Dropout(dropout)

    # pylint: disable=arguments-differ
    def forward(
        self,
        x: Tensor = None,
        memory: Tensor = None,
        src_mask: Tensor = None,
        trg_mask: Tensor = None,
    ) -> Tensor:
        """
        순전파를 수행합니다.
        
        :param x: 디코더 입력 텐서 [B, T_trg, D]
        :param memory: 인코더 출력 텐서 [B, T_src, D]
        :param src_mask: 소스 마스크 [B, 1, T_src]
        :param trg_mask: 타겟 마스크 [B, T_trg, T_trg]
        :return: 출력 텐서 [B, T_trg, D]
        """
        # 셀프 어텐션 (디코더)
        x_norm = self.x_layer_norm(x)
        h1 = self.trg_trg_att(x_norm, x_norm, x_norm, mask=trg_mask)
        h1 = self.dropout(h1) + x

        # 소스 어텐션 (인코더-디코더)
        h1_norm = self.dec_layer_norm(h1)
        h2 = self.src_trg_att(memory, memory, h1_norm, mask=src_mask)

        # Feed-forward
        o = self.feed_forward(self.dropout(h2) + h1)
        return o

