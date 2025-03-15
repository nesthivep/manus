package main

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strconv"
)

// AnyToStr 任意类型数据转string
func AnyToStr(i interface{}) (string, error) {
	if i == nil {
		return "", nil
	}

	v := reflect.ValueOf(i)
	if v.Kind() == reflect.Ptr {
		if v.IsNil() {
			return "", nil
		}
		v = v.Elem()
	}

	switch v.Kind() {
	case reflect.String:
		return v.String(), nil
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return strconv.FormatInt(v.Int(), 10), nil
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		return strconv.FormatUint(v.Uint(), 10), nil
	case reflect.Float32:
		return strconv.FormatFloat(v.Float(), 'f', -1, 32), nil
	case reflect.Float64:
		return strconv.FormatFloat(v.Float(), 'f', -1, 64), nil
	case reflect.Complex64:
		return fmt.Sprintf("(%g+%gi)", real(v.Complex()), imag(v.Complex())), nil
	case reflect.Complex128:
		return fmt.Sprintf("(%g+%gi)", real(v.Complex()), imag(v.Complex())), nil
	case reflect.Bool:
		return strconv.FormatBool(v.Bool()), nil
	case reflect.Slice, reflect.Map, reflect.Struct, reflect.Array:
		str, _ := json.Marshal(i)
		return string(str), nil
	default:
		return "", fmt.Errorf("unable to cast %#v of type %T to string", i, i)
	}
}
