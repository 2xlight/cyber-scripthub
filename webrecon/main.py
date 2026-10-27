from http import scan_http
from tools import run_ffuf, run_parameters, fingerprint
from urls import normalize_urls, deduplicate
from output import save_results

target = "https://example.com"

def main():
    target = input("Target: ").strip() #no strip

    http_data = scan_http(target) #response http

    directories = run_ffuf(target) #ffuf
    parameters = run_parameters(target) #param
    technologies = fingerprint(target) #fingerprint

    urls = http_data["urls"] + directories + parameters
    #url in list 
    urls = normalize_urls(urls)
    urls = deduplicate(urls)
    #chuan hoa

    save_results(
        http_data,
        directories,
        parameters,
        technologies,
        urls
    )
    #luu tru ket qua


if __name__ == "__main__":
    main()
    #chay