# -*- coding: utf-8 -*-
"""
사주 해석(풀이) 엔진 — 웹(lotto.html)과 동일 로직의 파이썬 버전
--------------------------------------------------
십신(十神)·십이운성(十二運星) 계산 + 일간/오행/운세/방위 해석 텍스트 생성.

* 주의 *  계산(십신·십이운성 배속)은 정통 명리 규칙 그대로지만, 풀이 문장과
용신(부족 오행 근사)은 표준 원리를 바탕으로 작성한 '간략 해석'이다.
"""

from saju_core import GAN, JI, GAN_OHENG, JI_OHENG

# 오행 생/극
OH_GEN = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
OH_CTL = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}

GAN_NATURE = {
    "갑": ("큰 나무(甲木)", "곧고 진취적입니다. 리더십과 뚝심, 명예를 중시하며 밀고 나가는 대들보형이에요."),
    "을": ("화초·덩굴(乙木)", "부드럽고 유연합니다. 섬세한 처세와 뛰어난 적응력, 은근한 끈기가 강점이에요."),
    "병": ("태양(丙火)", "밝고 정열적입니다. 표현력과 추진력이 좋고 사람을 끄는 화통함이 있어요."),
    "정": ("등불·달빛(丁火)", "따뜻하고 섬세합니다. 은근한 헌신과 집중력, 속 깊은 배려가 매력이에요."),
    "무": ("큰 산·대지(戊土)", "듬직하고 포용력이 큽니다. 중심을 잡아주는 신뢰와 안정감이 강점이에요."),
    "기": ("옥토·정원(己土)", "온화하고 실속 있습니다. 꼼꼼한 관리와 현실 감각이 뛰어나요."),
    "경": ("강철·원석(庚金)", "강직하고 결단력이 있습니다. 의리와 추진력, 승부욕이 돋보여요."),
    "신": ("보석·예도(辛金)", "예리하고 세련됐습니다. 완성도와 자존심, 뛰어난 심미안을 지녔어요."),
    "임": ("바다·큰물(壬水)", "지혜롭고 포용력이 큽니다. 활동적이고 스케일이 큰 사람이에요."),
    "계": ("이슬·시냇물(癸水)", "총명하고 섬세합니다. 감성과 상상력, 유연한 소통이 강점이에요."),
}
OHENG_INFO = {
    "목": {"kw": "성장·명예·교육·인정", "lack": "새로운 시작과 성장·의욕"},
    "화": {"kw": "열정·표현·화려함·예술", "lack": "열정과 표현·활력"},
    "토": {"kw": "안정·신용·중재·부동산", "lack": "안정과 신용·중심"},
    "금": {"kw": "결단·재물·의리·규율", "lack": "결단과 마무리·재물"},
    "수": {"kw": "지혜·유연·소통·이동", "lack": "지혜와 유연함·소통"},
}
OHENG_DIR = {
    "목": ("동(東)쪽", ["강원", "경북", "대구", "울산"]),
    "화": ("남(南)쪽", ["부산", "경남", "전남", "광주", "제주"]),
    "토": ("중앙(中)", ["대전", "세종", "충북", "충남"]),
    "금": ("서(西)쪽", ["인천", "전북"]),
    "수": ("북(北)쪽", ["서울", "경기"]),
}

# 십신
BRANCH_MAIN = {"자": "계", "축": "기", "인": "갑", "묘": "을", "진": "무", "사": "병",
               "오": "정", "미": "기", "신": "경", "유": "신", "술": "무", "해": "임"}
SIPSIN_GROUP = {"비견": "비겁", "겁재": "비겁", "식신": "식상", "상관": "식상",
                "편재": "재성", "정재": "재성", "편관": "관성", "정관": "관성",
                "편인": "인성", "정인": "인성"}
GROUP_INFO = {
    "비겁": "자기 주관과 독립심이 강합니다. 경쟁력·추진력이 좋지만 고집·독단은 조심하면 좋아요.",
    "식상": "표현력과 재능, 활동성이 돋보입니다. 아이디어를 밖으로 펼치고 즐기는 기운이에요.",
    "재성": "재물 감각과 현실 감각이 뛰어납니다. 실리를 챙기고 성과를 만드는 기운이에요.",
    "관성": "책임감과 명예욕, 조직 적응력이 좋습니다. 규율과 자기관리가 강점이에요.",
    "인성": "학문·수용력과 보호받는 기운이 강합니다. 배우고 정리하며 내실을 다지는 힘이에요.",
}
# 십이운성
STAGE = ["장생", "목욕", "관대", "건록", "제왕", "쇠", "병", "사", "묘", "절", "태", "양"]
JANGSAENG = {"갑": "해", "병": "인", "무": "인", "경": "사", "임": "신",
             "을": "오", "정": "유", "기": "유", "신": "자", "계": "묘"}
STAGE_INFO = {
    "장생": "새싹처럼 시작하는 기운. 순수하고 성장 가능성이 큽니다.",
    "목욕": "다듬어지는 시기. 변화가 많고 감수성이 예민합니다.",
    "관대": "독립하는 기운. 자기 색이 뚜렷하고 진취적입니다.",
    "건록": "자립과 왕성함. 능력을 스스로 펼치는 힘이 강합니다.",
    "제왕": "기운이 최고조. 강하고 주도적이며 리더십이 있습니다.",
    "쇠": "노련하고 안정된 기운. 신중하고 내실을 챙깁니다.",
    "병": "예민하고 섬세한 기운. 배려심이 깊고 휴식이 필요합니다.",
    "사": "사색하는 기운. 조용히 파고들고 정신적입니다.",
    "묘": "갈무리하는 기운. 내향적이고 알뜰합니다.",
    "절": "끊고 전환하는 기운. 변화가 크고 결단이 필요합니다.",
    "태": "잉태·준비하는 기운. 새로운 가능성을 품습니다.",
    "양": "보살핌 속 성장하는 기운. 온화하고 뒷심이 있습니다.",
}


# 납음(納音) 60갑자 — lunar-python(정통 라이브러리)에서 추출·한글화, 교차검증됨
NAYIN = {"갑자": "해중금", "갑오": "사중금", "병인": "노중화", "병신": "산하화", "무진": "대림목", "무술": "평지목", "경오": "노방토", "경자": "벽상토", "임신": "검봉금", "임인": "금박금", "갑술": "산두화", "갑진": "복등화", "병자": "간하수", "병오": "천하수", "무인": "성두토", "무신": "대역토", "경진": "백랍금", "경술": "채천금", "임오": "양류목", "임자": "상자목", "갑신": "천중수", "갑인": "대계수", "병술": "옥상토", "병진": "사중토", "무자": "벽력화", "무오": "천상화", "경인": "송백목", "경신": "석류목", "임진": "장류수", "임술": "대해수", "을축": "해중금", "을미": "사중금", "정묘": "노중화", "정유": "산하화", "기사": "대림목", "기해": "평지목", "신미": "노방토", "신축": "벽상토", "계유": "검봉금", "계묘": "금박금", "을해": "산두화", "을사": "복등화", "정축": "간하수", "정미": "천하수", "기묘": "성두토", "기유": "대역토", "신사": "백랍금", "신해": "채천금", "계미": "양류목", "계축": "상자목", "을유": "천중수", "을묘": "대계수", "정해": "옥상토", "정사": "사중토", "기축": "벽력화", "기미": "천상화", "신묘": "송백목", "신유": "석류목", "계사": "장류수", "계해": "대해수"}


def nayin_of(pillar_str):
    return NAYIN.get(pillar_str, "")


def gongmang(pillar_str):
    """일주 간지 -> 공망(空亡) 두 지지."""
    g = GAN.index(pillar_str[0])
    z = JI.index(pillar_str[1])
    base = (z - g) % 12
    return JI[(base + 10) % 12], JI[(base + 11) % 12]


def ten_god_stem(day_gi, t_gi):
    d_oh, t_oh = GAN_OHENG[day_gi], GAN_OHENG[t_gi]
    same = (day_gi % 2) == (t_gi % 2)
    if d_oh == t_oh:
        return "비견" if same else "겁재"
    if OH_GEN[d_oh] == t_oh:
        return "식신" if same else "상관"
    if OH_CTL[d_oh] == t_oh:
        return "편재" if same else "정재"
    if OH_CTL[t_oh] == d_oh:
        return "편관" if same else "정관"
    return "편인" if same else "정인"


def ten_god_branch(day_gi, ji_char):
    return ten_god_stem(day_gi, GAN.index(BRANCH_MAIN[ji_char]))


def twelve_stage(day_gan, ji_char):
    start = JI.index(JANGSAENG[day_gan])
    yang = GAN.index(day_gan) % 2 == 0
    pos = JI.index(ji_char)
    steps = (pos - start) % 12 if yang else (start - pos) % 12
    return STAGE[steps]


def relation(p_elem, d_elem):
    if OH_GEN.get(d_elem) == p_elem:
        return ("인성(도움운)", "이번 회차의 기운이 당신을 북돋아 줍니다. 주변의 도움과 귀인의 기운이 따르는 흐름이에요.")
    if OH_GEN.get(p_elem) == d_elem:
        return ("식상(표현운)", "당신의 기운을 밖으로 펼치는 흐름입니다. 즐겁게 도전하면 좋은 날이에요.")
    if OH_CTL.get(p_elem) == d_elem:
        return ("재성(재물운)", "재물의 기운과 맞닿는 흐름! 로또 같은 재미엔 반가운 상징이에요.")
    if OH_CTL.get(d_elem) == p_elem:
        return ("관성(절제운)", "절제와 신중함이 어울리는 흐름이에요. 큰 기대보다 가벼운 재미로 즐기세요.")
    return ("비겁(협력운)", "나와 같은 기운이 겹치는 날이에요. 경쟁 속 협력과 동료의 기운이 함께합니다.")


def sipsin_summary(saju):
    """8글자의 십신을 집계해 {그룹: 개수}와 대표 그룹을 반환."""
    ps = saju["pillars"]
    day_gi = GAN.index(ps["일주"].gan)
    counts = {"비겁": 0, "식상": 0, "재성": 0, "관성": 0, "인성": 0}
    for key in ("년주", "월주", "시주"):        # 천간 (일간 제외)
        if key in ps:
            counts[SIPSIN_GROUP[ten_god_stem(day_gi, GAN.index(ps[key].gan))]] += 1
    for key in ("년주", "월주", "일주", "시주"):  # 지지
        if key in ps:
            counts[SIPSIN_GROUP[ten_god_branch(day_gi, ps[key].ji)]] += 1
    dom = max(counts.items(), key=lambda x: x[1])[0]
    return counts, dom


def build_reading(saju, draw_gan_oh, yongsin, draw_iljin, region_stats=None, region_top=None):
    """풀이 섹션 리스트 [(제목, [줄, ...]), ...] 반환."""
    ps = saju["pillars"]
    ilgan = saju["ilgan"]
    p_elem = GAN_OHENG[GAN.index(ilgan)]
    oc = saju["oheng_count"]
    lacks = [o for o in oc if oc[o] == 0]
    muchs = [o for o in oc if oc[o] >= 3]

    sections = []
    nat = GAN_NATURE[ilgan]
    sections.append((f"나는 어떤 사람? (일간 {ilgan})", [f"{nat[0]} — {nat[1]}"]))

    oh_lines = []
    if muchs:
        oh_lines.append(f"{'·'.join(muchs)} 기운이 강합니다.")
    if lacks:
        need = ", ".join(OHENG_INFO[o]["lack"] for o in lacks)
        oh_lines.append(f"{'·'.join(lacks)} 기운이 부족 → {need}의 기운을 채우면 좋아요.")
    if not oh_lines:
        oh_lines.append("오행이 비교적 고르게 분포해 균형이 좋은 사주예요.")
    sections.append(("오행 분석", oh_lines))

    counts, dom = sipsin_summary(saju)
    cnt_str = ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1]) if v)
    sections.append(("십신(十神) 분석", [f"가장 두드러진 기운은 [{dom}]. {GROUP_INFO[dom]}", f"({cnt_str})"]))

    # 납음·공망
    ju = str(ps["일주"])
    gm = gongmang(ju)
    nayin_parts = [f"{lbl} {str(ps[key])}·{nayin_of(str(ps[key]))}"
                   for key, lbl in (("년주", "년"), ("월주", "월"), ("일주", "일"), ("시주", "시")) if key in ps]
    sections.append(("납음(納音)·공망(空亡)", [
        f"일주 {ju} = {nayin_of(ju)}",
        "  ".join(nayin_parts),
        f"공망: {gm[0]}·{gm[1]} — 비어서 채움이 필요한 자리로 봅니다."]))

    day_gan = ps["일주"].gan
    stage_parts = []
    for key, label in (("년주", "년지"), ("월주", "월지"), ("일주", "일지"), ("시주", "시지")):
        if key in ps:
            stage_parts.append(f"{label} {ps[key].ji}·{twelve_stage(day_gan, ps[key].ji)}")
    day_stage = twelve_stage(day_gan, ps["일주"].ji)
    sections.append((f"십이운성 (일지 {ps['일주'].ji}·{day_stage})",
                     [STAGE_INFO[day_stage], "  ".join(stage_parts)]))

    rel = relation(p_elem, draw_gan_oh)
    sections.append((f"이번 회차 운세 [{rel[0]}]", [rel[1]]))

    reason = (f"가장 필요한 기운은 [{yongsin}({OHENG_INFO[yongsin]['kw']})]. "
              f"이 기운을 채우는 오행수리(끝자리) 번호에 무게를 두고, "
              f"추첨일 일진 {draw_iljin}의 {draw_gan_oh} 기운을 더해 골랐습니다.")
    sections.append(("왜 이 번호인가", [reason]))

    d_name, regions = OHENG_DIR[yongsin]
    region_lines = [f"{yongsin} 기운을 채우기 좋은 방향은 [{d_name}].",
                    "추천 지역: " + ", ".join(regions)]
    if region_stats:
        ranked = sorted(((rg, region_stats.get(rg, 0)) for rg in regions), key=lambda x: -x[1])
        best = ranked[0]
        line = f"이 중 {best[0]}에서 1등이 가장 많이 나왔어요 ({best[1]}회)"
        if region_top and region_top.get(best[0]):
            t = region_top[best[0]][0]
            line += f", 대표 명당 {t[0]}({t[1]}회)"
        region_lines.append(line + ".")
    sections.append(("행운의 방위·지역", region_lines))
    return sections
