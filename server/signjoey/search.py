# coding: utf-8
"""
Greedy 및 Beam Search 디코딩 알고리즘
"""
import torch
import torch.nn.functional as F
from torch import Tensor
import numpy as np

from signjoey.decoders import Decoder, TransformerDecoder
from signjoey.embeddings import Embeddings
from signjoey.helpers import tile


__all__ = ["greedy", "transformer_greedy", "beam_search"]


def greedy(
    src_mask: Tensor,
    embed: Embeddings,
    bos_index: int,
    eos_index: int,
    max_output_length: int,
    decoder: Decoder,
    encoder_output: Tensor,
    encoder_hidden: Tensor,
) -> tuple:
    """
    Greedy 디코딩. 각 타임스텝에서 가장 높은 확률을 가진 토큰을 선택합니다.
    이 함수는 순환 디코더를 위한 recurrent_greedy와
    Transformer 디코더를 위한 transformer_greedy를 호출하는 래퍼입니다.

    :param src_mask: 소스 입력에 대한 마스크, </s> 이후 위치는 0
    :param embed: 타겟 임베딩
    :param bos_index: 어휘에서 <s>의 인덱스
    :param eos_index: 어휘에서 </s>의 인덱스
    :param max_output_length: 가설의 최대 길이
    :param decoder: greedy 디코딩에 사용할 디코더
    :param encoder_output: attention을 위한 인코더 은닉 상태
    :param encoder_hidden: 디코더 초기화를 위한 인코더 마지막 상태
    :return: (출력 배열, attention 점수 배열)
    """

    if isinstance(decoder, TransformerDecoder):
        # Transformer greedy 디코딩
        greedy_fun = transformer_greedy
    else:
        # 순환 greedy 디코딩
        greedy_fun = recurrent_greedy

    return greedy_fun(
        src_mask=src_mask,
        embed=embed,
        bos_index=bos_index,
        eos_index=eos_index,
        max_output_length=max_output_length,
        decoder=decoder,
        encoder_output=encoder_output,
        encoder_hidden=encoder_hidden,
    )


def recurrent_greedy(
    src_mask: Tensor,
    embed: Embeddings,
    bos_index: int,
    eos_index: int,
    max_output_length: int,
    decoder: Decoder,
    encoder_output: Tensor,
    encoder_hidden: Tensor,
) -> tuple:
    """
    Greedy 디코딩: 각 스텝에서 가장 높은 점수를 받는 단어를 선택합니다.
    순환 디코더용 버전.

    :param src_mask: 소스 입력에 대한 마스크, </s> 이후 위치는 0
    :param embed: 타겟 임베딩
    :param bos_index: 어휘에서 <s>의 인덱스
    :param eos_index: 어휘에서 </s>의 인덱스
    :param max_output_length: 가설의 최대 길이
    :param decoder: greedy 디코딩에 사용할 디코더
    :param encoder_output: attention을 위한 인코더 은닉 상태
    :param encoder_hidden: 디코더 초기화를 위한 인코더 마지막 상태
    :return:
        - stacked_output: 출력 가설 (인덱스의 2D 배열),
        - stacked_attention_scores: attention 점수 (3D 배열)
    """
    batch_size = src_mask.size(0)
    prev_y = src_mask.new_full(
        size=[batch_size, 1], fill_value=bos_index, dtype=torch.long
    )
    output = []
    attention_scores = []
    hidden = None
    prev_att_vector = None
    finished = src_mask.new_zeros((batch_size, 1)).byte()

    # pylint: disable=unused-variable
    for t in range(max_output_length):
        # 단일 스텝 디코드
        logits, hidden, att_probs, prev_att_vector = decoder(
            encoder_output=encoder_output,
            encoder_hidden=encoder_hidden,
            src_mask=src_mask,
            trg_embed=embed(prev_y),
            hidden=hidden,
            prev_att_vector=prev_att_vector,
            unroll_steps=1,
        )
        # logits: batch x time=1 x vocab (logits)

        # greedy 디코딩: 각 스텝에서 어휘에 대한 arg max 선택
        next_word = torch.argmax(logits, dim=-1)  # batch x time=1
        output.append(next_word.squeeze(1).detach().cpu().numpy())
        prev_y = next_word
        attention_scores.append(att_probs.squeeze(1).detach().cpu().numpy())
        # batch, max_src_lengths
        # 이전 심볼이 <eos>인지 확인
        is_eos = torch.eq(next_word, eos_index)
        finished += is_eos
        # 배치의 모든 요소에 대해 <eos>에 도달하면 예측 중단
        if (finished >= 1).sum() == batch_size:
            break

    stacked_output = np.stack(output, axis=1)  # batch, time
    stacked_attention_scores = np.stack(attention_scores, axis=1)
    return stacked_output, stacked_attention_scores


# pylint: disable=unused-argument
def transformer_greedy(
    src_mask: Tensor,
    embed: Embeddings,
    bos_index: int,
    eos_index: int,
    max_output_length: int,
    decoder: Decoder,
    encoder_output: Tensor,
    encoder_hidden: Tensor,
) -> tuple:
    """
    Transformer를 위한 특수 greedy 함수, 다르게 작동하므로.
    Transformer는 모든 이전 상태를 기억하고 그들에게 attention합니다.

    :param src_mask: 소스 입력에 대한 마스크, </s> 이후 위치는 0
    :param embed: 타겟 임베딩 레이어
    :param bos_index: 어휘에서 <s>의 인덱스
    :param eos_index: 어휘에서 </s>의 인덱스
    :param max_output_length: 가설의 최대 길이
    :param decoder: greedy 디코딩에 사용할 디코더
    :param encoder_output: attention을 위한 인코더 은닉 상태
    :param encoder_hidden: 인코더 최종 상태 (Transformer에서는 미사용)
    :return:
        - stacked_output: 출력 가설 (인덱스의 2D 배열),
        - stacked_attention_scores: attention 점수 (3D 배열)
    """

    batch_size = src_mask.size(0)

    # 배치의 각 문장에 대해 BOS 심볼로 시작
    ys = encoder_output.new_full([batch_size, 1], bos_index, dtype=torch.long)

    # subsequent 마스크는 디코더 순전파에서 이것과 교차됨
    trg_mask = src_mask.new_ones([1, 1, 1])
    finished = src_mask.new_zeros((batch_size)).byte()

    for _ in range(max_output_length):

        trg_embed = embed(ys)  # 이전 토큰을 임베딩

        # pylint: disable=unused-variable
        with torch.no_grad():
            logits, out, _, _ = decoder(
                trg_embed=trg_embed,
                encoder_output=encoder_output,
                encoder_hidden=None,
                src_mask=src_mask,
                unroll_steps=None,
                hidden=None,
                trg_mask=trg_mask,
            )

            logits = logits[:, -1]
            _, next_word = torch.max(logits, dim=1)
            next_word = next_word.data
            ys = torch.cat([ys, next_word.unsqueeze(-1)], dim=1)

        # 이전 심볼이 <eos>인지 확인
        is_eos = torch.eq(next_word, eos_index)
        finished += is_eos
        # 배치의 모든 요소에 대해 <eos>에 도달하면 예측 중단
        if (finished >= 1).sum() == batch_size:
            break

    ys = ys[:, 1:]  # BOS 심볼 제거
    return ys.detach().cpu().numpy(), None


# pylint: disable=too-many-statements,too-many-branches
def beam_search(
    decoder: Decoder,
    size: int,
    bos_index: int,
    eos_index: int,
    pad_index: int,
    encoder_output: Tensor,
    encoder_hidden: Tensor,
    src_mask: Tensor,
    max_output_length: int,
    alpha: float,
    embed: Embeddings,
    n_best: int = 1,
) -> tuple:
    """
    크기 k의 Beam search.
    OpenNMT-py에서 영감을 받아 Transformer에 맞게 수정했습니다.

    각 디코딩 스텝에서 가장 가능성 있는 k개의 부분 가설을 찾습니다.

    :param decoder: 디코더
    :param size: 빔 크기
    :param bos_index: BOS 토큰 인덱스
    :param eos_index: EOS 토큰 인덱스
    :param pad_index: PAD 토큰 인덱스
    :param encoder_output: 인코더 출력
    :param encoder_hidden: 인코더 은닉 상태
    :param src_mask: 소스 마스크
    :param max_output_length: 최대 출력 길이
    :param alpha: 길이 패널티를 위한 `alpha` 인자
    :param embed: 임베딩
    :param n_best: 이만큼의 가설을 반환, <= beam (현재는 1만)
    :return:
        - stacked_output: 출력 가설 (인덱스의 2D 배열),
        - stacked_attention_scores: attention 점수 (3D 배열)
    """
    assert size > 0, "빔 크기는 >0이어야 합니다."
    assert n_best <= size, "{} 개의 최선의 가설만 반환할 수 있습니다.".format(size)

    # 초기화
    transformer = isinstance(decoder, TransformerDecoder)
    batch_size = src_mask.size(0)
    att_vectors = None  # Transformer에서는 사용하지 않음

    # 순환 모델만: RNN 은닉 상태 초기화
    # pylint: disable=protected-access
    if not transformer:
        hidden = decoder._init_hidden(encoder_hidden)
    else:
        hidden = None

    # 인코더 상태와 디코더 초기 상태를 beam_size만큼 타일링
    if hidden is not None:
        hidden = tile(hidden, size, dim=1)  # layers x batch*k x dec_hidden_size

    encoder_output = tile(
        encoder_output.contiguous(), size, dim=0
    )  # batch*k x src_len x enc_hidden_size
    src_mask = tile(src_mask, size, dim=0)  # batch*k x 1 x src_len

    # Transformer만: 타겟 마스크 생성
    if transformer:
        trg_mask = src_mask.new_ones([1, 1, 1])  # Transformer만
    else:
        trg_mask = None

    # 배치의 요소 번호 매기기
    batch_offset = torch.arange(
        batch_size, dtype=torch.long, device=encoder_output.device
    )

    # 확장 배치의 요소 번호 매기기, 즉 각 배치 요소의 beam size 복사본
    beam_offset = torch.arange(
        0, batch_size * size, step=size, dtype=torch.long, device=encoder_output.device
    )

    # 배치의 각 요소에 대해 확장할 상위 빔 크기 가설 추적
    # (아직 "살아있는" 가설)
    alive_seq = torch.full(
        [batch_size * size, 1],
        bos_index,
        dtype=torch.long,
        device=encoder_output.device,
    )

    # 첫 번째 스텝에서 첫 번째 빔에 완전한 확률 부여
    topk_log_probs = torch.zeros(batch_size, size, device=encoder_output.device)
    topk_log_probs[:, 1:] = float("-inf")

    # 완성된 가설을 보유하는 구조
    hypotheses = [[] for _ in range(batch_size)]

    results = {
        "predictions": [[] for _ in range(batch_size)],
        "scores": [[] for _ in range(batch_size)],
        "gold_score": [0] * batch_size,
    }

    for step in range(max_output_length):

        # 이것은 다음 예측을 하기 위해 디코더에 공급할 예측된 문장의 부분을 결정합니다.
        # Transformer의 경우, 지금까지의 완전한 예측된 문장을 공급합니다.
        # 순환 모델의 경우, 이전 타겟 단어 예측만 공급합니다.
        if transformer:  # Transformer
            decoder_input = alive_seq  # 지금까지의 완전한 예측
        else:  # 순환
            decoder_input = alive_seq[:, -1].view(-1, 1)  # 마지막 단어만

        # 현재 가설 확장
        # 단일 스텝 디코드
        # logits: 최종 softmax를 위한 logits
        # pylint: disable=unused-variable
        trg_embed = embed(decoder_input)
        logits, hidden, att_scores, att_vectors = decoder(
            encoder_output=encoder_output,
            encoder_hidden=encoder_hidden,
            src_mask=src_mask,
            trg_embed=trg_embed,
            hidden=hidden,
            prev_att_vector=att_vectors,
            unroll_steps=1,
            trg_mask=trg_mask,  # Transformer만을 위한 subsequent 마스크
        )

        # Transformer의 경우 이 시점까지 모든 타임스텝에 대해 예측을 했으므로
        # 마지막 타임스텝에 대해서만 알고 싶습니다.
        if transformer:
            logits = logits[:, -1]  # 마지막 타임스텝만 유지
            hidden = None  # Transformer에서는 유지할 필요 없음

        # batch*k x trg_vocab
        log_probs = F.log_softmax(logits, dim=-1).squeeze(1)

        # 빔 확률을 곱함 (=logprobs 더하기)
        log_probs += topk_log_probs.view(-1).unsqueeze(1)
        curr_scores = log_probs.clone()

        # 길이 패널티 계산
        if alpha > -1:
            length_penalty = ((5.0 + (step + 1)) / 6.0) ** alpha
            curr_scores /= length_penalty

        # log_probs를 가능성 목록으로 평탄화
        curr_scores = curr_scores.reshape(-1, size * decoder.output_size)

        # 현재 최선의 top k 가설 선택 (평탄화된 순서)
        topk_scores, topk_ids = curr_scores.topk(size, dim=-1)

        if alpha > -1:
            # 원래 log probs 복구
            topk_log_probs = topk_scores * length_penalty
        else:
            topk_log_probs = topk_scores.clone()

        # 평탄화된 순서에서 빔 원점과 실제 단어 ID 재구성
        topk_beam_index = topk_ids.div(decoder.output_size)
        topk_ids = topk_ids.fmod(decoder.output_size)

        # beam_index를 평면 표현의 batch_index에 매핑
        batch_index = topk_beam_index + beam_offset[
            : topk_beam_index.size(0)
        ].unsqueeze(1)
        select_indices = batch_index.view(-1)

        # 최신 예측 추가
        alive_seq = torch.cat(
            [alive_seq.index_select(0, select_indices), topk_ids.view(-1, 1)], -1
        )  # batch_size*k x hyp_len

        is_finished = topk_ids.eq(eos_index)
        if step + 1 == max_output_length:
            is_finished.fill_(True)
        # 종료 조건은 상위 빔이 완료되었는지 여부
        end_condition = is_finished[:, 0].eq(True)

        # 완성된 가설 저장
        if is_finished.any():
            predictions = alive_seq.view(-1, size, alive_seq.size(-1))
            for i in range(is_finished.size(0)):
                b = batch_offset[i]
                if end_condition[i]:
                    is_finished[i].fill_(True)
                finished_hyp = is_finished[i].nonzero().view(-1)
                # 이 배치에 대한 완성된 가설 저장
                for j in finished_hyp:
                    # 예측이 두 개 이상의 EOS를 가지고 있는지 확인.
                    # 두 개 이상의 EOS가 있으면 예측이 이미 가설에 추가되었어야 하므로 다시 추가할 필요가 없습니다.
                    if (predictions[i, j, 1:] == eos_index).nonzero().numel() < 2:
                        hypotheses[b].append(
                            (
                                topk_scores[i, j],
                                predictions[i, j, 1:],
                            )  # start_token 무시
                        )
                # 배치가 끝에 도달하면 n_best 가설 저장
                if end_condition[i]:
                    best_hyp = sorted(hypotheses[b], key=lambda x: x[0], reverse=True)
                    for n, (score, pred) in enumerate(best_hyp):
                        if n >= n_best:
                            break
                        results["scores"][b].append(score)
                        results["predictions"][b].append(pred)
            non_finished = end_condition.eq(False).nonzero().view(-1)
            # 모든 문장이 번역되면 더 이상 진행할 필요 없음
            # pylint: disable=len-as-condition
            if len(non_finished) == 0:
                break
            # 다음 스텝을 위해 완료된 배치 제거
            topk_log_probs = topk_log_probs.index_select(0, non_finished)
            batch_index = batch_index.index_select(0, non_finished)
            batch_offset = batch_offset.index_select(0, non_finished)
            alive_seq = predictions.index_select(0, non_finished).view(
                -1, alive_seq.size(-1)
            )

        # 인덱스, 출력 및 마스크 재정렬
        select_indices = batch_index.view(-1)
        encoder_output = encoder_output.index_select(0, select_indices)
        src_mask = src_mask.index_select(0, select_indices)

        if hidden is not None and not transformer:
            if isinstance(hidden, tuple):
                # LSTM의 경우, 상태는 텐서의 튜플
                h, c = hidden
                h = h.index_select(1, select_indices)
                c = c.index_select(1, select_indices)
                hidden = (h, c)
            else:
                # GRU의 경우, 상태는 단일 텐서
                hidden = hidden.index_select(1, select_indices)

        if att_vectors is not None:
            att_vectors = att_vectors.index_select(0, select_indices)

    def pad_and_stack_hyps(hyps, pad_value):
        filled = (
            np.ones((len(hyps), max([h.shape[0] for h in hyps])), dtype=int) * pad_value
        )
        for j, h in enumerate(hyps):
            for k, i in enumerate(h):
                filled[j, k] = i
        return filled

    # results에서 stacked outputs로
    assert n_best == 1
    # 현재는 n_best=1에서만 작동
    final_outputs = pad_and_stack_hyps(
        [r[0].cpu().numpy() for r in results["predictions"]], pad_value=pad_index
    )

    return final_outputs, None
