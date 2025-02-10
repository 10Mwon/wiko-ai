import time
import textwrap
import re
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Selenium 옵션 설정 (headless 모드 사용)
options = webdriver.ChromeOptions()
options.add_argument("--headless")            # 브라우저 창 없이 실행
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--incognito")           # 인코그니토 모드 사용

# 결과를 저장할 딕셔너리
# key: (cciNo, cnpClsNo), value: {"texts": 텍스트 리스트, "title": 페이지 타이틀}
results = {}

# cciNo, cnpClsNo 조합 생성
combinations = []
for cci in [1, 2]:
    if cci == 1:
        combinations.append((cci, 1))
    elif cci == 2:
        combinations.append((cci, 1))
        combinations.append((cci, 2))

# 각 조합에 대해 크롤링 진행
for cciNo, cnpClsNo in combinations:
    # URL 구성 (csmSeq와 ccfNo는 고정)
    url = f"https://www.easylaw.go.kr/CSP/CnpClsMain.laf?csmSeq=1703&ccfNo=1&cciNo={cciNo}&cnpClsNo={cnpClsNo}"
    print(f"크롤링 시작: cciNo={cciNo}, cnpClsNo={cnpClsNo}")
    
    # Chrome 드라이버 실행 및 URL 접근
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    
    # <div class="ovDivbox"> 요소가 로드될 때까지 최대 10초 대기
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ovDivbox"))
        )
    except Exception as e:
        print(f"cciNo={cciNo}, cnpClsNo={cnpClsNo} - ovDivbox 요소 대기 실패:", e)
    
    # 추가 로딩을 위해 잠시 대기 (필요 시 조정)
    time.sleep(2)
    
    # 페이지의 HTML 코드 가져오기
    html = driver.page_source
    driver.quit()
    
    # BeautifulSoup로 HTML 파싱
    soup = BeautifulSoup(html, "html.parser")
    
    # 페이지 타이틀 추출 (예: <div id="pageTitle" class="page_title"><h4>비자발급인정서에 의한 발급</h4>...</div>)
    page_title_div = soup.find("div", id="pageTitle")
    if page_title_div:
        h4 = page_title_div.find("h4")
        if h4:
            page_title_text = h4.get_text(strip=True)
        else:
            page_title_text = f"cciNo{cciNo}_cnpClsNo{cnpClsNo}"
    else:
        page_title_text = f"cciNo{cciNo}_cnpClsNo{cnpClsNo}"
    
    # <div class="ovDivbox"> 요소들 추출 (본문 내용)
    ov_divboxes = soup.find_all("div", class_="ovDivbox")
    texts = []
    if ov_divboxes:
        for idx, div in enumerate(ov_divboxes, start=1):
            # get_text(separator="\n", strip=True)로 단락 구분(줄바꿈) 보존
            content = div.get_text(separator="\n", strip=True)
            # 각 줄(단락)별로 공백 제거 후 다시 결합
            paragraphs = [line.strip() for line in content.splitlines() if line.strip()]
            combined_text = "\n".join(paragraphs)
            # "인쇄체크"라는 문구 제거
            combined_text = combined_text.replace("인쇄체크", "")
            texts.append(combined_text)
    else:
        texts.append("No ovDivbox found.")
    
    # 결과 저장
    results[(cciNo, cnpClsNo)] = {"texts": texts, "title": page_title_text}
    print(f"크롤링 완료: cciNo={cciNo}, cnpClsNo={cnpClsNo}\n")

# 저장할 폴더를 "비자"로 지정
save_directory = "비자"
if not os.path.exists(save_directory):
    os.makedirs(save_directory)

# 각 조합별 결과를 별도의 JSON 파일로 저장 (파일 이름은 페이지 타이틀 사용)
for (cciNo, cnpClsNo), data in results.items():
    text_content = data["texts"]
    title = data["title"]
    # 파일 이름으로 사용할 수 없는 문자는 제거
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    
    # 파일 저장 경로를 "비자" 폴더로 지정, JSON 파일 확장자 사용
    output_filename = os.path.join(save_directory, f"{safe_title}.json")
    
    # JSON 데이터 구성
    json_data = {
        "title": title,
        "content": text_content
    }
    
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    
    print(f"크롤링 결과가 '{output_filename}' 파일에 저장되었습니다.")
