import os
import re
import json
import requests
from bs4 import BeautifulSoup

# 기본 도메인 (상대 URL 처리를 위해)
base_url = "https://eps.hrdkorea.or.kr"

# 메인 페이지 URL (여기서 sub-menu를 추출)
main_url = "https://eps.hrdkorea.or.kr/e9/user/employment/employment.do?method=employGuidCompany"

# HTTP 요청 시 사용할 헤더
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

# 저장할 폴더 ("고용허가제\EPS외국인고용지원")
save_directory = r"고용허가제\EPS외국인고용지원"
if not os.path.exists(save_directory):
    os.makedirs(save_directory)

# 메인 페이지 요청 및 파싱
main_response = requests.get(main_url, headers=headers)
if main_response.status_code != 200:
    print("메인 페이지를 불러오지 못했습니다. 상태 코드:", main_response.status_code)
    exit()

main_soup = BeautifulSoup(main_response.text, "html.parser")

# <div id="sub-menu"> 내부의 모든 <a> 태그 추출 (href 속성이 있는 태그)
sub_menu_div = main_soup.find("div", id="sub-menu")
if not sub_menu_div:
    print("메인 페이지에서 <div id='sub-menu'> 요소를 찾지 못했습니다.")
    exit()

a_tags = sub_menu_div.find_all("a", href=True)

# 중복 제거를 위한 URL 집합 생성 (href가 "#"으로 시작하는 링크는 제외)
unique_urls = set()
for a in a_tags:
    href = a["href"].strip()
    if href.startswith("#"):
        continue
    if href.startswith("/"):
        full_url = base_url + href
    else:
        full_url = href
    unique_urls.add(full_url)

print("추출된 고유 URL:")
for url in unique_urls:
    print(url)

# 각 고유 URL에 대해 크롤링 진행 (중복은 한 번씩만 실행)
for url in unique_urls:
    print("\n크롤링 시작:", url)
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("페이지를 불러오지 못했습니다. 상태 코드:", resp.status_code)
        continue

    page_soup = BeautifulSoup(resp.text, "html.parser")
    
    # [수정] 저장할 내용: <div id="normal_page"> 내부의 텍스트만 추출 (줄바꿈 보존)
    normal_page_div = page_soup.find("div", id="normal_page")
    if normal_page_div:
        text_content = normal_page_div.get_text(separator="\n", strip=True)
        text_content = text_content.replace("본문건너뛰기", "")
    else:
        text_content = "No contents found."

    # 파일 이름 생성:
    # 우선, <div id="contents"> 내부의 <h3> 태그 내의 <img> 태그에서 alt 속성 값 추출
    contents_div = page_soup.find("div", id="contents")
    alt_text = None
    if contents_div:
        h3_tag = contents_div.find("h3")
        if h3_tag:
            img_tag = h3_tag.find("img")
            if img_tag and img_tag.has_attr("alt"):
                alt_text = img_tag["alt"].strip()
    # alt 속성이 없으면 URL의 쿼리 문자열에서 method 매개변수 값 추출
    if not alt_text:
        method_match = re.search(r"method=([^&]+)", url)
        if method_match:
            alt_text = method_match.group(1)
        else:
            alt_text = "default"

    # JSON 데이터 구성
    data = {
        "url": url,
        "title": alt_text,
        "content": text_content
    }

    # 파일 이름에 사용할 수 없는 문자는 제거하고 .json 확장자 추가
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", alt_text) + ".json"
    output_filepath = os.path.join(save_directory, safe_filename)
    
    # 추출한 데이터를 JSON 파일에 저장 (UTF-8 인코딩)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"크롤링 결과가 '{output_filepath}' 파일에 저장되었습니다.")
