package main

import (
	"log"
	"os"
	"strings"
)

// 保存日志到文件
func Log(v ...any) {
	// 打开文件
	file, err := os.OpenFile("wails.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		return
	}
	defer file.Close()
	// 设置logger
	logToFile := log.New(file, "WailsLog: ", log.LstdFlags)
	log.Println(v...)
	// 写入日志
	logToFile.Println(v...)
}

// 保存日志到文件
func Logf(format string, v ...any) {
	if !strings.HasSuffix(format, "\n") {
		format = format + "\n"
	}
	// 打开文件
	file, err := os.OpenFile("wails.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		return
	}
	defer file.Close()
	// 设置logger
	logToFile := log.New(file, "WailsLog: ", log.LstdFlags)
	log.Printf(format, v...)
	// 写入日志
	logToFile.Printf(format, v...)
}
