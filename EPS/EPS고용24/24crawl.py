import os
import re
import json
import requests
from bs4 import BeautifulSoup

# HTTP 요청 시 사용할 헤더
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

save_directory = r"base_data"
if not os.path.exists(save_directory):
    os.makedirs(save_directory)

# tabGb 값 6과 7에 대해 반복
for tabGb in [6, 7]:
    # URL 구성: tabGb 값을 두 자리 숫자 형식으로 (06, 07)
    url = f"https://www.eps.go.kr/eo/EmployJobProc.eo?tabGb={tabGb:02d}"
    print(f"\n크롤링 시작: {url}")
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"페이지를 불러오지 못했습니다. 상태 코드: {response.status_code}")
        continue

    soup = BeautifulSoup(response.text, "html.parser")
    
    # 파일 이름 추출용: <div id="contents"> 내부의 <h3> 태그 내의 <img> 태그의 alt 속성 사용
    contents_div = soup.find("div", id="contents")
    if not contents_div:
        print("<div id='contents'> 요소를 찾지 못했습니다.")
        continue

    h3_tag = contents_div.find("h3")
    if h3_tag:
        img_tag = h3_tag.find("img")
        if img_tag and img_tag.has_attr("alt"):
            alt_text = img_tag["alt"].strip()
        else:
            alt_text = f"default_{tabGb:02d}"
    else:
        alt_text = f"default_{tabGb:02d}"

    # 저장할 내용 추출: <div id="print"> 내부의 텍스트 (줄바꿈 보존)
    print_div = soup.find("div", id="print")
    if print_div:
        text_content = print_div.get_text(separator="\n", strip=True)
        # <div id="print"> 내부에서 <h4 class="typeE"> 태그의 텍스트 추출 (파일명에 포함)
        h4_tag = print_div.find("h4", class_="typeE")
        if h4_tag:
            type_text = h4_tag.get_text(strip=True)
        else:
            type_text = ""
    else:
        text_content = "No contents found."
        type_text = ""
    
    # 파일 이름 생성: alt_text와 type_text를 결합 (두 값 사이에 "_" 추가)
    combined_name = alt_text
    if type_text:
        combined_name += "_" + type_text

    # 파일 이름에 사용할 수 없는 특수문자 제거 후 .json 확장자 추가
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", combined_name) + ".json"
    output_filepath = os.path.join(save_directory, safe_filename)
    
    # JSON 데이터 구성
    data = {
        "url": url,
        "title": alt_text,
        "type": type_text,
        "content": text_content
    }
    
    # 추출한 데이터를 JSON 파일에 저장 (UTF-8 인코딩)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"크롤링 결과가 '{output_filepath}' 파일에 저장되었습니다.")
