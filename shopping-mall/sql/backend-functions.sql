-- schema.sql 이후 실행합니다. Step 2의 동시 장바구니 담기에 사용합니다.
-- 기존 설치에도 재실행할 수 있으며 테이블 구조나 데이터를 변경하지 않습니다.
BEGIN;
CREATE OR REPLACE FUNCTION public.add_cart_item(p_product_id uuid, p_quantity integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_user_id uuid := auth.uid();
    v_product public.products%ROWTYPE;
    v_item public.cart_items%ROWTYPE;
BEGIN
    IF v_user_id IS NULL THEN RAISE EXCEPTION 'AUTH_REQUIRED' USING ERRCODE = '42501'; END IF;
    IF p_product_id IS NULL OR p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'INVALID_CART_INPUT';
    END IF;
    PERFORM 1 FROM public.users WHERE id = v_user_id FOR KEY SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'USER_NOT_FOUND'; END IF;
    SELECT * INTO v_product FROM public.products WHERE id = p_product_id FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'PRODUCT_NOT_FOUND'; END IF;
    IF NOT v_product.is_active THEN RAISE EXCEPTION 'PRODUCT_INACTIVE'; END IF;
    INSERT INTO public.cart_items(user_id, product_id, quantity)
    VALUES (v_user_id, p_product_id, p_quantity)
    ON CONFLICT (user_id, product_id) DO UPDATE
        SET quantity = public.cart_items.quantity + EXCLUDED.quantity
    RETURNING * INTO v_item;
    IF v_item.quantity > v_product.stock THEN RAISE EXCEPTION 'INSUFFICIENT_STOCK'; END IF;
    RETURN to_jsonb(v_item);
END;
$$;
REVOKE ALL ON FUNCTION public.add_cart_item(uuid,integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.add_cart_item(uuid,integer) TO authenticated;
COMMIT;
