package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"strings"
)

var host = "http://localhost:8020"

type Body struct {
	Code int         `json:"code"`
	Msg  string      `json:"msg"`
	Data interface{} `json:"data"`
}

// 结构体中的变量命名首字母大写,不然不能被外部访问到
type Resp struct {
	Code int         `json:"code"`
	Data interface{} `json:"data"`
}

func buildResp(resp *http.Response, err error) Resp {
	// 确保在函数退出时关闭resp的主体
	defer resp.Body.Close()

	// 打印请求结果
	Logf("Http Resp: %v, err: %v\n", resp, err)
	if err != nil {
		// 网络请求处理错误
		Log("Network Error: ", err)
		return Resp{resp.StatusCode, err.Error()}
	}
	if resp.StatusCode != 200 {
		// 网络请求状态码异常
		Log("Http Resp Status Code Error: ", resp)
		return Resp{resp.StatusCode, resp.Status}
	}

	// 读取响应体
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		Log("Error Reading Response Body: ", err)
		return Resp{202, err.Error()}
	}

	// 打印响应内容
	Log("Http Response Body: ", string(body))
	// 判断返回内容类型
	// Log(resp)
	Logf("Content-Type=%v", resp.Header.Get("Content-Type"))
	contentType := resp.Header.Get("Content-Type")
	// 处理返回响应状态和内容
	var bodySt Body
	if !strings.HasPrefix(contentType, "application/json") {
		// 非json,直接返回
		return Resp{resp.StatusCode, string(body)}
	}

	// 序列化后返回
	err = json.Unmarshal(body, &bodySt)
	if err != nil {
		Log("Parse Body Json Faild: ", err)
		return Resp{202, err.Error()}
	}
	if bodySt.Code != 200 {
		return Resp{bodySt.Code, bodySt.Msg}
	}
	return Resp{bodySt.Code, bodySt.Data}
}

func buildReqUrl(uri string) string {
	if strings.HasPrefix(uri, "http") {
		return uri
	}
	return host + uri
}

// Go http请求 https://www.cnblogs.com/Xinenhui/p/17496684.html
// Get
func Get(uri string, param map[string]interface{}, header map[string]string) Resp {
	Logf("Get Uri: %s, Param: %s, Header: %s\n", uri, param, header)
	apiUrl := buildReqUrl(uri)

	//新建一个GET请求
	req, err := http.NewRequest("GET", apiUrl, nil)
	if err != nil {
		return Resp{202, err.Error()}
	}

	// 请求头部信息
	// Set时候，如果原来这一项已存在，后面的就修改已有的
	// Add时候，如果原本不存在，则添加，如果已存在，就不做任何修改
	for k, v := range header {
		req.Header.Set(k, v)
	}

	// url参数处理
	q := req.URL.Query()
	for k, v := range param {
		strOfV, err := AnyToStr(v)
		if err != nil {
			return Resp{202, err.Error()}
		}
		q.Set(k, strOfV)
	}
	req.URL.RawQuery = q.Encode()

	// 发送请求给服务端,实例化一个客户端
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return Resp{202, err.Error()}
	}
	return buildResp(resp, err)
}

// Post Json
func Post(uri string, param map[string]interface{}, header map[string]string) Resp {
	Logf("Post Json Uri: %s, Param: %s, Header: %s\n", uri, param, header)
	apiUrl := buildReqUrl(uri)

	// Json参数处理
	jsonStr, err := json.Marshal(param)
	if err != nil {
		Log("Error Marshalling Map To JSON: ", err)
		return Resp{202, err.Error()}
	}
	Logf("Post Json Body Payload: %s\n", string(jsonStr))

	// 新建一个POST请求
	req, err := http.NewRequest("POST", apiUrl, strings.NewReader(string(jsonStr)))
	if err != nil {
		return Resp{202, err.Error()}
	}
	// 请求头部信息
	// Set时候，如果原来这一项已存在，后面的就修改已有的
	// Add时候，如果原本不存在，则添加，如果已存在，就不做任何修改
	for k, v := range header {
		req.Header.Set(k, v)
	}
	// Post Json表单请求头
	req.Header.Add("Content-Type", "application/json")

	//发送请求给服务端,实例化一个客户端
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return Resp{202, err.Error()}
	}
	return buildResp(resp, err)
}

// Post Form
func PostForm(uri string, param map[string]interface{}, header map[string]string) Resp {
	Logf("Post Form Uri: %s, Param: %s\n", uri, param)
	apiUrl := buildReqUrl(uri)

	// PostForm参数处理
	urlMap := url.Values{}
	for k, v := range param {
		strOfV, err := AnyToStr(v)
		if err != nil {
			return Resp{202, err.Error()}
		}
		urlMap.Set(k, strOfV)
	}

	Logf("Post Form Body Payload: %s\n", urlMap.Encode())

	// 新建一个POST请求
	req, err := http.NewRequest("POST", apiUrl, strings.NewReader(urlMap.Encode()))
	if err != nil {
		return Resp{202, err.Error()}
	}
	// 请求头部信息
	// Set时候，如果原来这一项已存在，后面的就修改已有的
	// Add时候，如果原本不存在，则添加，如果已存在，就不做任何修改
	for k, v := range header {
		req.Header.Set(k, v)
	}
	// Post FormData表单请求头
	req.Header.Add("Content-Type", "application/x-www-form-urlencoded")

	//发送请求给服务端,实例化一个客户端
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return Resp{202, err.Error()}
	}
	return buildResp(resp, err)
}

// Del
func Del(uri string, param map[string]interface{}, header map[string]string) Resp {
	Logf("Del Uri: %s, Param: %s\n", uri, param)
	apiUrl := buildReqUrl(uri)

	//新建一个Del请求
	req, err := http.NewRequest("DELETE", apiUrl, nil)
	if err != nil {
		return Resp{202, err.Error()}
	}

	// 请求头部信息
	// Set时候，如果原来这一项已存在，后面的就修改已有的
	// Add时候，如果原本不存在，则添加，如果已存在，就不做任何修改
	for k, v := range header {
		req.Header.Set(k, v)
	}

	// url参数处理
	q := req.URL.Query()
	for k, v := range param {
		strOfV, err := AnyToStr(v)
		if err != nil {
			return Resp{202, err.Error()}
		}
		q.Set(k, strOfV)
	}
	req.URL.RawQuery = q.Encode()

	// 发送请求给服务端,实例化一个客户端
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return Resp{202, err.Error()}
	}
	return buildResp(resp, err)
}
